# Project Standards Review Remediation Design

**Date:** 2026-07-19 **Status:** owner-approved; implementation pending **Author:** session 2026-07-19

## Problem and goal

The Fable 5 review at `docs/fable-review/2026-07-19-project-standards-review.md` records 100 findings against the Catalog 5 implementation. Project Standards 5.0.2 is already published. The owner selected 5.1.0 for the verified corrections, requires Python 3.14 or newer on every consumer surface, prohibited deferrals, and prohibited unrelated features or cleanup.

The goal is to close every review finding with an evidence-backed final disposition and implement only the corrections compatible with the 5.1 release contract. A finding is closed by a correction, a narrower documented contract when the review overstates the defect, or a final rejection when the proposed change is invalid or incompatible. Rejected findings do not become backlog items.

## Approved approach

Use one compatibility-first correction train grouped by subsystem. Shared helpers are allowed only when two or more accepted findings require the same behavior. Each implementation task starts and ends with a finding-to-diff scope check and follows RED-GREEN-REFACTOR.

The rejected alternatives are:

1. Apply every reviewer suggestion literally. This would introduce previously-passing-to-failing transitions, require a major release, and expand the repository's GitHub Actions pinning policy.
2. Implement only High and Medium findings. This would defer verified Low corrections contrary to the owner decision.
3. Mix review work with the existing TODO queue, CI redesign, engine retirement, or release-proof tooling. None of those changes corrects a finding in this review.

## Scope audit

### Included

- Source, test, documentation, schema, workflow, and script corrections tied to F-001 through F-100.
- Consumer-lock schema 1.1 for the create-only absence state required by F-003.
- New immutable payload versions required to correct released payload behavior or managed consumer artifacts.
- Payload digests, family indexes, Catalog 5 declarations, source projections, generated schemas, the local lock, and live dogfood artifacts mechanically required by those payload versions.
- Maintained specification and usage-document synchronization where an accepted correction changes an intended contract.
- Changelog, version, status, and handoff updates required to prepare and close out release 5.1.0.

### Excluded

- New product capabilities, commands, packages, configuration options, or consumer workflows. F-029 only restores the already-supported `--view` parser surface.
- Python 3.13 or older compatibility, compatibility syntax, or a lower-runtime matrix.
- New `testing`-branch workflow triggers; the existing asymmetry is documented under F-035.
- Deleting the separately named coherence workflow; its intentional duplicate status is documented under F-039.
- A new SHA-pinning policy for GitHub-owned actions; F-086 retains the established major-tag policy.
- Agent Handoff engine deletion, future-standard work, repository rulesets, issue or pull-request administration, TODO-queue work, and release-proof infrastructure.
- Any ignored `.superpowers/sdd/**` scratch artifacts discovered by the documentation inventory.
- Publishing or moving 5.1.0 tags before the implementation gate passes and the owner explicitly authorizes publication.

### Per-task scope gate

Before each task, record its finding IDs, permitted source files, permitted tests, and required generated outputs. After the focused gate, inspect `git diff --name-status` and `git diff --check`. A changed file must be one of:

1. named by the finding;
2. the focused regression test for that finding;
3. an immutable payload or mutable family source needed by that finding;
4. a deterministic digest, catalog, schema, projection, lock, or live dogfood output caused by that payload; or
5. release/specification documentation whose statement became false because of the accepted correction.

Anything else is removed from the task rather than justified after the fact.

## Final disposition ledger

### Direct corrections

The following 55 findings are accepted with the review's essential remedy and bounded to their verified trigger:

`F-001`, `F-002`, `F-005`, `F-007`, `F-008`, `F-009`, `F-012`, `F-013`, `F-014`, `F-015`, `F-016`, `F-017`, `F-018`, `F-022`, `F-024`, `F-025`, `F-027`, `F-029`, `F-031`, `F-032`, `F-037`, `F-038`, `F-042`, `F-043`, `F-044`, `F-046`, `F-048`, `F-049`, `F-051`, `F-052`, `F-054`, `F-055`, `F-058`, `F-060`, `F-061`, `F-062`, `F-063`, `F-064`, `F-065`, `F-066`, `F-067`, `F-068`, `F-070`, `F-071`, `F-073`, `F-076`, `F-080`, `F-081`, `F-082`, `F-088`, `F-089`, `F-091`, `F-092`, `F-093`, and `F-099`.

### Adjusted corrections

| Findings | Final correction |
| --- | --- |
| F-003 | Add a versioned `create_only_absences` lock partition instead of retaining a stale `LockedUnit`. |
| F-004, F-057 | Emit stable `CP-BUSY`, exit 1, and matching JSON across initialized command surfaces. Do not broadly reclassify render failures. |
| F-006 | Keep Python 3.14 PEP 758 syntax. State that consumer `python3` must resolve to 3.14 or newer in current Agent Handoff and authoring contracts. |
| F-010 | Remove unenforced shape knobs from the mutable model and Agent Handoff 1.2 rather than adding stricter validation. |
| F-011 | Treat a successfully emitted legacy inventory as report success: return 0 in human and JSON modes on selected and fallback paths, while retaining findings in the content. |
| F-019 | Use a lexical, string-aware JSONC sanitizer; do not use a trailing-comma regex that can alter strings. |
| F-021 | Detect anchors and aliases throughout the frontmatter token stream, preserve the file unchanged, warn, and retain exit 0 rather than corrupting bytes or introducing a new failure. |
| F-023 | Resolve child schemas through a root-context validator and distinguish valid local references from controlled missing-reference errors. |
| F-026 | Derive lock and JSON modes from the real parsers while preserving currently accepted argparse abbreviations. Parse uncertainty chooses the safe write lock. |
| F-028 | Correct the test-layer documentation, including the actual suite directories and that installed-wrapper tests may require package-index access. |
| F-030 | Put the F-007 link normalization in one internal Agent Handoff helper; callers retain their own fence masking. |
| F-033 | Guard the currently unreachable missing-resource lookup without inventing a stale-lock trigger. |
| F-034 | Add only `permissions: contents: read`; do not reorder unrelated workflow keys. |
| F-035 | Document that only graph validation runs on `testing`; do not add six hosted triggers. |
| F-036 | Make unsupported zipapp jsonschema calls fail loudly while preserving every supported `validate-id.pyz` path. |
| F-039 | Retain the separately named coherence workflow and document that the duplicate run is intentional. |
| F-040 | Combine atomic no-clobber publication with descriptor-relative, no-follow parent handling; a partial replace-only change is insufficient. |
| F-041 | Distinguish installed-distribution `OSError`, emit a visible warning, and preserve the 5.1-compatible fallback outcome. |
| F-045 | Require `agent_handoff` in `load_registry`, but retain direct `Registry` constructor defaults. |
| F-047 | Consolidate all six typed control-plane digest copies in `control_plane.codec`; do not create a broader package-contract API. |
| F-050, F-059 | Replace message sniffing with narrow typed authorization and absent-companion errors while preserving existing exit classifications. |
| F-053 | Remove the unused parameter at the five actual call sites, not the review's claimed six. |
| F-056 | Standardize reserved authority temporary names and clean only validated stale regular temporaries under an exclusive lock or sanctioned recovery. |
| F-069 | Name Standard Bundle Authoring 2.2 after the correction payload is authored, rather than stopping at the review-time 2.1 value. |
| F-072 | Share the ordinary frontmatter scope constants while retaining `.standards/**` as an ADR-only augmentation. |
| F-074 | Load document types lazily with UTF-8 and route failures through the existing configuration boundary; preserve no unnecessary public constant. |
| F-075 | Retain `fix_file` for import compatibility but quarantine it as a legacy direct-write library path prohibited inside unified control-plane execution. |
| F-078 | Use a callable replacement and anchor exactly one rewrite beneath `markdown.frontmatter`; unrelated `include` blocks remain untouched. |
| F-079, F-085 | Discover canonical catalog sources once, load and hash package families once, and validate each catalog against immutable repository copies. |
| F-083 | Retain the graph checks as documented defense-in-depth for manually constructed repositories; payload validation remains authoritative. |
| F-084 | Use a typed output-path error and classify output-write `OSError` explicitly; do not inspect message text. |
| F-086 | Keep major tags for GitHub-owned actions. Add only the missing `# v8.3.2` comment to the already-SHA-pinned CLI Documentation `setup-uv` line. |
| F-090 | Share option/ID resolution and reuse the already-loaded legacy configuration during self-validation. |
| F-094 | Collect H1-H6 only for anchor slugs, retain H2-H4 section parsing, and reuse F-009 fence masking. |
| F-096 | Document that declared artifact mode is the consumer contract and source-tree executable bits are not; do not mutate released file modes. |
| F-097 | Add the 42 missing `-> None` annotations and remove the filename comment. Do not add `from __future__ import annotations` under Python 3.14. |
| F-098 | Anchor the genuine repository fixtures in all 12 listed modules, not the review title's ten, while preserving deliberately relative generated-code paths. |
| F-100 | Pass the exact prebuilt candidate wheel into compatibility CI and publish that managed workflow through Python Tooling 1.2. |

### Final no-change dispositions

These findings are closed, not deferred, and create no future TODO item:

| Finding | Final disposition |
| --- | --- |
| F-020 | Confirmed inconsistency, but aligning check/write changes a currently successful default outcome and requires a major release. Documentation cannot contradict the current parity contract. No 5.1 change. |
| F-077 | Rejected. Exit 1 is the explicit per-tool contract for both sync tools; exit 2 would be a policy change. |
| F-087 | Rejected. The underscore name is cosmetic and cannot change declared provider resources; immutable payload churn would be unrelated cleanup. |
| F-095 | Rejected. The provider output schema already makes `found=true` with missing Markdown unreachable at the authoritative boundary. |

## Architecture and data flow

```text
review finding
    -> failing focused regression
    -> smallest source or documentation correction
    -> new immutable payload only when released bytes or managed output changes
    -> digest, family, catalog, projection, lock, and dogfood synchronization
    -> focused gate and scope-diff audit
    -> full 5.1.0 retained gate
```

### Consumer-lock schema 1.1

F-003 cannot reuse a prior `LockedUnit`: its required semantic and content hashes would claim absent bytes still exist. Schema 1.1 adds `create_only_absences`, whose records contain only path, adapter, normalized scope, owners, shared identity, package versions, and provenance. Absence and live-artifact natural keys are unique across both partitions.

The reader accepts schema 1.0 and treats the new partition as empty. Bootstrap and successful mutation write canonical 1.1. The planner moves a selected create-only unit from `artifacts` to `create_only_absences` when the consumer removes it, refreshes owner/version facts from the current selection, and never resurrects it on later reconciliations. If the consumer recreates the unit it can return to the live partition. Disabling the package relinquishes the absence record.

For a 5.0.x lock already affected by F-003, infer absence only when the lock's applied package version and effective configuration digest still match the current resolution and the create-only unit is missing. A changed package or configuration is not guessed into a tombstone.

### Shared correction primitives

Shared code is limited to repeated defects already in the ledger:

- a string-aware JSONC sanitizer for F-019 and mutable runtime inspection;
- one fence-masked structural view for F-009, F-027, and F-094 while preserving original text for output and byte budgets;
- typed error classes for F-004, F-050, F-057, F-059, and F-084;
- one control-plane byte-digest function for F-047;
- canonical catalog discovery and one loaded package repository for F-079 and F-085; and
- descriptor-relative no-follow/no-clobber filesystem helpers for F-040, F-055, and F-088 where their existing writers share the same invariant.

No helper becomes public unless a released payload already requires a stable import. F-025 is the one explicit exception: it adds public validator names while permanently retaining the private aliases imported by immutable Markdown Frontmatter 1.2.

### Immutable payload corrections

Released payload directories remain byte- and mode-immutable. Catalog 5 keeps every old version advertised and advances only compatible ordinary defaults.

| New payload | Findings that require it |
| --- | --- |
| `agent-handoff@1.2` | F-006, F-007, F-010, F-024, F-027, plus synchronized runtime prerequisites |
| `project-spec@1.2` | F-002 reusable-workflow input handling |
| `markdown-frontmatter@1.3` | F-025 public imports and F-034 managed caller permissions |
| `python-tooling@1.2` | F-100 exact candidate-wheel compatibility workflow |
| `cli-documentation@1.2` | accepted F-086 setup-uv version comment |
| `standard-bundle-authoring@2.2` | F-006 Python floor and F-096 executable-mode contract |

No Markdown Tooling payload is cut because the rejected action-pinning proposal is the only review item that would require one.

## Compatibility and error behavior

- Python 3.14 or newer is the consumer floor. Current PEP 758 exception syntax remains canonical, and tests do not add future-annotation semantics.
- Valid, previously-passing consumer documents and workflows must not newly fail. Corrections that reject malformed provider output, invalid manifests, unsafe concurrent publication, or repository-authoring errors do not tighten a valid consumer document contract.
- `legacy-report` exit 0 means the inventory was emitted, not that migration is complete. The report retains error findings; only clean validation establishes migration.
- Anchor-bearing frontmatter is preserved with a warning and success rather than rewritten unsafely or newly failed.
- Lock contention is always `CP-BUSY` with exit 1. Other render failures retain the documented render contract.
- The F-041 fallback remains behavior-compatible but becomes observable through a warning.

## Testing and verification

Every behavioral correction begins with a failing regression that proves the exact trigger. Parser, sanitizer, lock-codec, and line-boundary work should use property tests where invariants are stronger than isolated examples: round-trip preservation, no string corruption, natural-key uniqueness, deterministic ordering, and CRLF/LF equivalence.

After each task:

1. run the focused test in RED, then GREEN;
2. run Ruff and BasedPyright over the touched Python surface;
3. run the affected package reconstruction or source/wheel parity tests;
4. inspect the diff against the task's finding/file allowlist; and
5. run generated checks only when the task changes a payload, schema, catalog, or live managed artifact.

The final gate uses the extracted candidate wheel first on `PYTHONPATH` and includes:

- Ruff format/check and BasedPyright strict;
- package validation, graph validation, schema generation, catalog rendering, payload projection, and release classification against 5.0.2;
- ordinary pytest with coverage, the four-worker compatibility matrix using the exact prebuilt wheel, serial performance tests, and the coverage report;
- Prettier, markdownlint, coherence after `npm ci`, managed Markdown validation, and Agent Handoff validation through the installed-wheel probe; and
- `pip-audit`, build, wheel/sdist content parity, immutable prior-payload comparison, and clean `git diff --check`.

Release classification must be `minor`, and the prepared tool version is 5.1.0. Tag creation, tag movement, and GitHub release publication remain separate until explicitly authorized after this gate.

## Completion criteria

- Every F-001 through F-100 appears in exactly one direct, adjusted, or final no-change disposition.
- No released payload bytes or modes changed in place.
- The six new payloads reconstruct exactly, their digests and projections match, and old exact selectors remain available.
- Consumer-lock 1.0 reads successfully and the first successful write produces canonical 1.1 without resurrecting deleted create-only content.
- All accepted focused regressions and the complete retained gate pass from the candidate wheel.
- The final diff contains only review corrections, required generated consequences, and synchronized contract/release documentation.
- No rejected finding or unrelated queue item is left as a deferred task.
