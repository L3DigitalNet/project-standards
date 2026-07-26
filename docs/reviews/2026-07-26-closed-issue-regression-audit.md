---
schema_version: '1.1'
id: 'reference-0crjzl-closed-issue-regression-audit'
title: 'Project Standards 5.8.0 Closed-Issue Regression Audit'
description: 'Read-only verification that every closed GitHub issue remained resolved before the next correction train was specified.'
doc_type: 'reference'
status: 'active'
created: '2026-07-26'
updated: '2026-07-26'
reviewed: '2026-07-26'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'regression'
  - 'review'
  - 'validation'
aliases: []
related:
  - 'docs/specs/2026-07-26-v5-adoption-integrity-correction-train-spec.md'
  - 'docs/plans/2026-07-25-v5-adoption-integrity-correction-train-plan.md'
---

# Project Standards 5.8.0 Closed-Issue Regression Audit

This read-only audit ran before revising the correction-train specification or implementation plan. It verified the complete live GitHub closed-issue set, the exact published 5.8.0 wheel, current source-to-wheel projection, focused issue behavior, and the full repository gate. No closed issue had regressed.

The audit found one durability gap rather than a present regression: issue #21's current and shipped guidance is correct, but its semantic documentation contract lacks a dedicated committed regression test. The next correction train therefore requires a durable issue-to-proof map and a permanent #21 guard.

## Scope and identities

| Item | Verified value |
| --- | --- |
| Repository branch | `testing` |
| Closed GitHub issues | #3 and #8-#31 |
| Closed-issue count | 25 |
| Published release | Project Standards 5.8.0 |
| Published wheel | `project_standards-5.8.0-py3-none-any.whl` |
| Wheel SHA-256 | `5fe1b8c6dc2e06675365f5ac9be2bc884e83be7eeb21b2b842e8a67ab18b73f4` |
| Source/runtime drift since tag | No runtime, test, package, workflow, or release-policy diff from `v5.8.0^{}` to the audited `HEAD` |
| Source-to-wheel projection | Catalogs, families, and payloads byte-equal |
| Opus audit result | `verified_with_advisories`; no confirmed regression |
| Opus result SHA-256 | `b32cf24469ac29251fadd14fa4391541f7959fd966d6e21d36204c5d9b31dc87` |

GitHub numbers #1, #2, #4-#7, #33, and #34 are pull requests, not issue records. They are therefore outside the closed-issue regression set: #1, #2, and #4-#6 are closed dependency/fix pull requests; #7, #33, and #34 are open dependency pull requests.

## Method

1. Queried live GitHub issue records and confirmed that the closed issue set was exactly #3 and #8-#31.
2. Resolved the published 5.8.0 wheel and verified its SHA-256.
3. Extracted that wheel and placed it first on `PYTHONPATH` for installed-distribution-dependent tests.
4. Compared the audited checkout with `v5.8.0^{}` across runtime, tests, packages, workflows, and release policy.
5. Compared published wheel catalogs, families, and payloads with the current source projection.
6. Ran focused regressions and direct semantic assertions for every closed issue.
7. Ran the full source, installed-wheel, package, graph, schema, projection, coherence, Markdown, managed-document, dependency-audit, performance, and handoff gates.
8. Submitted a bounded symlink-free repository snapshot to independent Opus review and verified the canonical result.

The transient focused selector reported 151 passing tests. Its exact selection expression was not retained in repository state, so that number is corroborating historical context, not a reproducible acceptance authority. The full commands below and the future committed issue-to-proof map are the durable authorities.

## Per-issue result

| Issue | Released correction | Audit evidence | Result |
| --- | --- | --- | --- |
| #3 | External/spec IDs, token hygiene, and opt-in formatter authority | Spec-validator ID/reference/license suites; Markdown Tooling/coherence workflow tests | Resolved |
| #8 | Subset-aware V4-to-V5 migration | Migration namespace/default/unknown-setting fixtures and compatibility rows | Resolved |
| #9 | Released V4 platform-version lineage | Legacy platform-tag migration fixtures and release-byte lineage | Resolved |
| #10 | Released `.editorconfig` digest lineage | Known-digest package/migration fixtures | Resolved |
| #11 | Bounded takeover of mixed consumer/managed files | Bounded-block/shared-configuration migration and preservation fixtures | Resolved |
| #12 | Consumer-owned Python/Markdown workflow and script relinquishment | Ownership-transition provider, migration, and convergence fixtures | Resolved |
| #13 | Consumer-owned CLI Documentation workflow relinquishment | CLI Documentation ownership schema/provider/migration fixtures | Resolved |
| #14 | Python Tooling key-level checker/pytest ownership | Exact key-preservation and lock-transition fixtures | Resolved |
| #15 | Strict-markdownlint-safe managed instruction blocks | Package payload and Markdown lint/coherence fixtures | Resolved |
| #16 | Preserved `prettier: false` migration | Markdown Tooling 1.7 migration and disabled/enabled caller fixtures | Resolved |
| #17 | Project Specification empty-corpus success | Exact selected-version validate/lint empty-corpus fixtures | Resolved |
| #18 | Agent Handoff managed-envelope size accounting | Size-report/shape fixtures with managed blocks and malformed lookalikes | Resolved |
| #19 | Absolute Project Specification finding coordinates | Legacy/selected validate/lint line-coordinate fixtures | Resolved |
| #20 | Python Tooling additional source roots | Schema/provider/reconstruction/migration tests for checker, coverage, and Ruff roots | Resolved |
| #21 | Truthful package-option migration guidance | Five direct semantic assertions over `UPGRADING.md` and Python Tooling 1.6/1.7/1.8 source and shipped adoption guides | Resolved; committed guard missing |
| #22 | Self-sufficient conflict diagnostics | Typed finding, JSON schema, text/JSON CLI, and governing-option fixtures | Resolved |
| #23 | Informative migration-preview exits | Applicable/blocked/inapplicable preview exit-code fixtures | Resolved |
| #24 | Per-root coverage scoping | Python Tooling 1.7 schema/provider/migration and exact predecessor-byte fixtures | Resolved |
| #25 | Anchored TOML comment preservation | TOML adapter span/comment and end-to-end reconcile fixtures | Resolved |
| #26 | Frontmatter/Prettier quote fixed point | `tests/test_frontmatter_prettier_parity.py` corpus and original issue case | Resolved |
| #27 | Legacy Markdown lint-config byte form | `tests/package_contract/test_markdown_tooling_legacy_forms.py` and observed-consumer fixture | Resolved |
| #28 | Markdown Frontmatter workflow ownership | `tests/package_contract/test_markdown_frontmatter_workflow_ownership.py` | Resolved |
| #29 | Explicit formatter mode and named-skip diagnostics | `tests/test_format_frontmatter.py` and `tests/test_validate_frontmatter.py` named-file cases | Resolved |
| #30 | Factual legacy-authority note | Command-resolution, frontmatter, and control-plane CLI route tests | Resolved |
| #31 | Configurable pytest collection roots | `tests/package_contract/test_python_tooling_test_paths.py` and provider/migration fixtures | Resolved |

## Full verification results

| Gate | Result |
| --- | --- |
| Ruff format | 367 files already formatted |
| Ruff check | Passed |
| BasedPyright strict | 0 errors, 0 warnings, 0 notes |
| Ordinary pytest/coverage lane | 3,266 passed, 90 deselected |
| Compatibility lane | 85 passed |
| Performance lane | 5 passed |
| Coverage | 90% |
| Python dependency audit | No known vulnerabilities; local unpublished project skipped as expected |
| Package validation | Passed |
| Package graph validation | Passed |
| Generated schema check | Passed |
| Payload projection check | Passed |
| Coherence | 8 passed |
| Prettier | All matched files passed |
| markdownlint | 837 files, 0 issues |
| Managed Markdown | 34 files passed |
| Plan validation | 18 tasks and 25 then-plan-local requirements passed |
| Agent Handoff | Validators exited 0; pre-existing line-length advisories only |
| Git whitespace | `git diff --check` passed |

The Node audit reported one development-only chain as two High entries: `markdownlint-cli2` to `js-yaml` under GHSA-pm4m-ph32-ghv5. `npm audit --omit=dev` was clean. This is not a closed-issue regression. Dependency remediation is separately scoped because local/CI parity is part of the fixes for issues #15 and #27.

## Reproducible command surface

The audit used the repository's ordinary extracted-wheel gate:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv build --wheel --out-dir "$AUDIT_WHEEL_OUT"
python -m zipfile -e "$AUDIT_WHEEL_OUT"/project_standards-*.whl "$AUDIT_WHEEL_RUNTIME"
export PYTHONPATH="$AUDIT_WHEEL_RUNTIME${PYTHONPATH:+:$PYTHONPATH}"
uv run coverage erase
uv run coverage run --source=project_standards -m pytest -m "not performance and not compatibility"
uv run pytest -m compatibility -n 4 --dist load --max-worker-restart=0
uv run pytest -m performance
uv run coverage report
uv run pip-audit
uv run project-standards standards validate-packages --root . --json
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards sync-payload-projection --root . --check
npm ci
uv run pytest tests/coherence -v
npm run format:check
npx markdownlint-cli2
uv run project-standards validate
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
uv run project-standards agent-handoff size-report --repo .
uv run project-standards agent-handoff shape-check --repo .
git diff --check
```

The published baseline wheel was separately resolved rather than treating a new source build as equivalent. Source-to-tag and source-to-wheel comparisons were read-only.

## Conclusion and planning consequence

No pre-existing regression must be repaired before revising the current plan. The correction-train specification and plan may proceed, but implementation must begin by replacing the transient focused selector with a committed issue-to-proof map, adding the dedicated #21 semantic guard, and executing that contract against both the exact 5.8.0 baseline and the eventual candidate.
