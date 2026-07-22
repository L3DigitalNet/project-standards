# Upgrade Compatibility Fixes Design

**Date:** 2026-07-21 **Status:** owner-authorized for autonomous implementation and release **Author:** Codex with Chris Purcell / L3DigitalNet

## Problem and goal

Project Standards 5.3.1 exposes two consumer upgrade defects.

Python Tooling 1.4 owns the complete `[tool.basedpyright]`, `[tool.pyright]`, and `[tool.pytest.ini_options]` tables. A V4 consumer that carries a legitimate extra key such as `extraPaths` or `pythonpath` therefore conflicts with the package's fixed whole-table value during migration. Those keys are load-bearing import-search configuration, but the closed package schema neither models them nor offers a safe ownership boundary that preserves them.

Markdown Tooling 1.5 renders configured glob patterns as ordinary prose in its managed instruction block. Patterns such as `**/*.md` are parsed as emphasis and fail MD037/MD049 when a consumer selects underscore-style emphasis. The managed block is control-plane-owned, so the consumer cannot repair it durably.

The goal is to make both previously blocked consumers pass without weakening their gates, modifying any released payload, or broadening control-plane engine behavior.

## Scope

In scope:

- author Python Tooling 1.5 as a compatible successor to 1.4;
- narrow the checker and pytest TOML contributions to the exact keys the package governs;
- preserve unrelated keys in those consumer tables through V4 migration, apply, reconciliation, and lock convergence;
- author Markdown Tooling 1.6 as a compatible successor to 1.5;
- render configured instruction-scope globs as inline code;
- retain all historical package versions and make 1.5/1.6 the Catalog 5 defaults;
- publish the compatible package additions as Project Standards 5.4.0;
- verify the exact release artifacts and hosted workflows, then close GitHub issues #14 and #15 with evidence.

Out of scope:

- changing the consumer option schemas to enumerate arbitrary third-party TOML keys;
- adding whole-file or whole-table `pyproject.toml` ownership escapes;
- modifying Python Tooling 1.4 or Markdown Tooling 1.5 bytes;
- changing markdownlint rule configuration or disabling additional rules;
- changing the control-plane TOML adapter or migration protocol.

## Requirements

| ID | Requirement |
| --- | --- |
| FR-001 | A V4 Python Tooling migration with consumer-owned `basedpyright.extraPaths` and `pytest.pythonpath` values must preview, apply, preserve both values byte-semantically, and converge without `CP-CONSUMER-CONFLICT`. |
| FR-002 | Python Tooling 1.5 must continue to manage every canonical checker and pytest key that 1.4 rendered, with exactly one selected checker family materialized and locked. |
| FR-003 | Python Tooling disable, re-enable, checker transition, exact-version selection, and same-major latest resolution must preserve lock integrity and retain all advertised historical payloads. |
| FR-004 | Markdown Tooling 1.6 instruction blocks must render every configured Markdown and structured-config glob in inline code and pass MD037/MD049 under underscore-style emphasis. |
| FR-005 | Catalog 5 must retain Python Tooling 1.4 and Markdown Tooling 1.5 while making 1.5 and 1.6 their compatible defaults. |
| FR-006 | Project Standards 5.4.0 must be built once, verified from its extracted wheel across the repository release gates, published from `main`, and accompanied by signed immutable `v5.4.0` and moving `v5` tags plus byte-matching GitHub assets. |
| FR-007 | GitHub issues #14 and #15 must close only after the published release and supporting verification are available. |
| NFR-001 | No released payload, immutable full-version tag, or historical catalog selection may change bytes or behavior. |
| NFR-002 | The fixes must not turn any previously passing consumer outcome into a failure; the tool release is therefore MINOR under `meta/versioning.md`. |
| NFR-003 | Focused regression tests must demonstrate RED before implementation and GREEN afterward; full release claims require fresh repository and hosted evidence. |

## Approved approach

### Python Tooling: key-level TOML ownership

Python Tooling 1.5 replaces the three whole-table declarations with managed key contributions.

For the selected checker table, the package owns only `include`, `typeCheckingMode`, `pythonVersion`, `pythonPlatform`, and `failOnWarnings`. Each key contribution retains the existing checker-selection predicate, so exactly one checker family remains materialized. For pytest, the package owns `minversion`, `testpaths`, `addopts`, and `markers`; `markers` is rendered explicitly as an array so the contribution has one total semantic value for every schema-valid configuration.

The provider renders one TOML value for each declared key scope. The existing TOML adapter already creates, updates, adopts, removes, and locks key scopes while retaining neighboring consumer keys and comments. Migration needs no special inference: because `extraPaths` and `pythonpath` are outside the desired scope set, they remain consumer-owned and no longer participate in equality classification.

Tests cover the issue fixture end to end, assert the preserved values after apply, inspect key-level lock scopes, prove second-plan convergence, and keep the existing checker lifecycle and source-versus-wheel reconstruction guarantees.

### Markdown Tooling: code-span glob rendering

Markdown Tooling 1.6 wraps each configured glob independently in backticks before joining the list. The option schema already excludes backticks from glob values, so no escaping grammar or fallback is required. The resulting prose remains readable while Markdown parsers treat the glob as code rather than emphasis.

Tests assert provider output for default and configured lists and run the pinned markdownlint implementation against the rendered block with MD037 enabled and MD049 set to `underscore`.

### Package and release integration

Both successor payloads are complete immutable copies with only their intended behavior, documentation, provider, manifest, and integrity changes. Family indexes and Catalog 5 retain old versions and advance compatible defaults. Source payload projections are regenerated from canonical version directories rather than hand-edited.

Because compatible consumer payload additions are MINOR under the repository contract, the release version is 5.4.0. The release follows the repository's `testing` to `main` workflow, uses one candidate wheel and sdist for all artifact-sensitive checks, updates changelog/status/handoff truth surfaces, publishes signed tags and GitHub assets, waits for the release-commit workflows, verifies downloaded asset hashes against the local artifacts, and only then closes the issues.

## Alternatives rejected

1. **Add `type_checker.extra_paths` and `pytest.pythonpath` options.** This handles two reported keys but leaves every other legitimate third-party table extension subject to the same conflict. Automatic V4 preservation would also require new migration snapshot or inference machinery; otherwise consumers would still need to re-declare existing values manually.
2. **Add a consumer-owned pyproject or table escape.** This preserves custom bytes by surrendering all standard enforcement for the affected surface. It is broader than the failure and makes later reacquisition another ownership boundary.
3. **Teach whole-table reconciliation to merge unknown keys.** This changes generic adapter ownership semantics and makes a managed table partly shared without expressing that split in the manifest. Existing key scopes already model the intended ownership directly.
4. **Disable MD037 and MD049 inside the managed block.** This hides future mistakes in control-plane-owned prose and weakens a consumer's selected lint policy.
5. **Render glob lists in a fenced block.** Correct but unnecessarily expands a compact instruction block and changes its visual hierarchy.

## Failure behavior

- A consumer value that differs at a key Python Tooling actually owns remains a blocking `CP-CONSUMER-CONFLICT`; only unrelated keys become preserved.
- A malformed or unsupported package configuration continues to fail closed through the existing option schema and provider validation.
- Switching checker selection removes the prior package-owned checker keys and creates the new selected keys. Consumer-only keys left in the old table are preserved because they were never locked by 1.5.
- Backticks in Markdown Tooling glob values remain schema-invalid, preventing an unescaped code-span delimiter from reaching rendering.
- Any historical payload drift, package graph conflict, projection drift, release-classification mismatch, failed gate, unsigned tag, failed hosted workflow, or artifact hash mismatch blocks publication or issue closure.

## Verification and acceptance

Implementation follows RED-GREEN-REFACTOR in this order:

1. Add the failing Python migration regression and prove the two whole-table conflicts.
2. Author Python Tooling 1.5 with key-level contributions and make the migration, lifecycle, integrity, catalog, and installed-wheel tests pass.
3. Add the failing strict-emphasis Markdown regression and prove MD037/MD049 findings.
4. Author Markdown Tooling 1.6 with code-span rendering and make provider/coherence tests pass.
5. Run focused package-contract and catalog suites, then the complete source and extracted-candidate release gates.
6. Publish 5.4.0 from `main`, verify tags, GitHub release metadata, all release-commit workflows, and downloaded asset hashes.
7. Close #14 and #15 with the released version and regression evidence.

Acceptance requires every FR/NFR above, a clean worktree, exact `main`/`testing`/remote parity after release, and no remaining open issue among #14/#15.
