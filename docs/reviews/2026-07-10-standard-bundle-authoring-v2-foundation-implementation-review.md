# Review: Standard Bundle Authoring V2 Foundation Implementation

**Plan:** `docs/superpowers/plans/2026-07-10-standard-bundle-authoring-v2-foundation.md`

**Governing spec:** `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (SPEC-BA02 rev 0.6)

**Implementation range:** `4e507d6` through the foundation closeout on `testing`

**Reviewer:** inline coding-agent whole-diff review, per owner direction

**Status:** approved for foundation closeout after resolving one Important finding; no open Critical or Important finding

## Verdict

The implementation satisfies the approved foundation boundary after one cross-surface CI packaging defect found by the full gate was corrected. It provides strict authoring declarations, deterministic load/validation/generation, release-baseline checks, and a proved installed-payload projection without activating V2 or adding consumer mutation. No package-specific branch, V1/V2 fact merge, unsafe undeclared read, schema drift, copied runtime payload, or requirement-status overclaim remains in the reviewed diff.

## Review Boundary

The review compared the complete implementation with SPEC-BA02 and the approved 15-task plan, with particular attention to the six closeout risks named by Task 15:

1. package-ID conditionals in shared V2 code;
2. V1 facts entering V2 models or validation;
3. repository or Git reads escaping declared safe paths;
4. generated schemas diverging from strict models;
5. regular files becoming a second installed-payload authority; and
6. traceability claiming runtime behavior that the foundation does not execute.

## Findings and Dispositions

### F1 — Important, resolved: CI performance gate drifted from its packaged and documented twins

Task 14 added the dedicated performance-marker invocation to `.github/workflows/check.yml` but did not update the byte-locked Python Tooling bundle or its copy/paste scaffold. The full suite caught the mismatch through `test_dogfoodable_templates_match_repo_root_byte_for_byte` and both current-repository V1 graph tests. The fix applies the same coverage exclusion and dedicated performance step to all three representations; focused dogfood, scaffold, and graph tests pass.

The same gate also showed Prettier trying to rewrite generated V2 schemas and digest-bound fixture JSON. Those bytes are owned by the schema generator and integrity fixtures, respectively. `.prettierignore` now names the three generated schemas and the package-contract fixture corpus, with a regression test locking that ownership boundary. Repository-wide Prettier passes.

### F2 — Minor, resolved: catalog freshness command used the wrong relative output

The plan's final catalog freshness command repeated the fixture path even though `--output` is root-relative; that would resolve to a nested nonexistent path. The plan now uses `--output expected/catalog.toml`, matching the CLI contract and the tracked golden. This changes no implementation or approved behavior.

The following boundaries are intentional, not findings:

- Provider models, entrypoint resource checks, phase/effect checks, and migration declarations are implemented, but providers are not executed. Provider filesystem/network spies and typed runtime output remain control-plane-core work.
- Adapter selectors and ownership conflicts are validated, but live TOML/JSONC/YAML/EditorConfig/Markdown mutation and byte preservation remain control-plane-core work.
- The symlink projection and installed-wheel parity are proved with synthetic V2 payloads. Every real standard must be reconstructed and rechecked before V5 activation.
- Release comparison and classification mechanisms are implemented, but no V2 catalog has been published and no current package is advertised through V2.

## Architecture Evidence

- Searches of `src/project_standards/package_contract/` found no real package ID or per-standard dispatch. Identity comparisons are generic graph ownership and relation checks.
- V2 discovery selects only regular `standard.toml` files whose bounded preamble declares `schema_version = "2.0"`; the V1 graph/runtime remains in its existing namespace.
- Family, payload, option-schema, catalog, projection, and released-Git reads are rooted in validated IDs, versions, safe relative paths, declared resources, or resolved Git commits.
- `generate-package-schemas --check` reports fresh checked-in model output.
- `sync-payload-projection --check` reports fresh output, and the repository contains no regular file under `src/project_standards/payloads/`.
- The full fixture validates three availability classes, all five catalog roles, whole/static/provider/shared outputs, relationship evidence, an extension, and automatic/manual migrations.
- Installed-wheel discovery runs with network construction disabled and matches normalized source manifests, aggregate digests, and inventories.
- One hundred randomized discovery orders produce identical findings, payload digests, schemas, and catalog bytes.
- The dedicated CI performance gate validates and renders 100 families, 1,000 payloads, and 10,000 declared units within the ten-second requirement.

## Traceability Decision

SPEC-BA02 rev 0.6 records only evidence proved by this plan. Declaration/model/integrity/catalog requirements are marked `Passing` where their complete requirement is exercised. Runtime providers, live adapters/preservation, installed parity for real packages, V2 publication, and current-package reconstruction remain `Partial` or `Not Started`. FR-024–FR-031 were not promoted to complete merely because reusable release primitives now exist.

## Verification

The fail-fast repository gate passes: Ruff format/check, BasedPyright strict, 1,693 tests, 93% branch coverage, `pip-audit`, clean `npm audit`, eight coherence tests, repository-wide Prettier, 224-file Markdownlint, frontmatter and strict spec validation, the V1 graph, V2 full-fixture validation, and schema/catalog/projection freshness. The focused package-contract suite contributes 309 tests after the formatter-ownership regression was added.
