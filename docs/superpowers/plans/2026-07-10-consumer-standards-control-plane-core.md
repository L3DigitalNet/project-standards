# Consumer Standards Control Plane Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved for execution after Round 1 review remediation. The review explicitly waived another round when the recommended stdlib wheel-extraction mechanism was used; that prerequisite and every other finding were resolved before execution.

**Goal:** Implement SPEC-CP01 MS-1 through MS-3 as a generic, offline control-plane engine: exact neutral bootstrap, strict config/catalog/lock state, catalog-scoped resolution, syntax-preserving virtual-tree planning, bounded provider execution, explicit executor-only apply, removal, and recovery.

**Architecture:** Add a `project_standards.control_plane` boundary that consumes the implemented V2 package-contract repository without package-ID branches. Pure loaders, resolvers, provider envelopes, adapters, and the virtual-tree planner produce a complete immutable plan before mutation. An exclusive executor rechecks whole-file preconditions, publishes staged files atomically, runs read-only verification, and writes the central lock last. Current package reconstruction, legacy YAML conversion, and release activation remain a separate follow-on plan.

**Tech Stack:** Python 3.14, Pydantic 2, JSON Schema Draft 2020-12, stdlib `tomllib`/`json`/`hashlib`/`fcntl`/`importlib`/`pathlib`, existing PyYAML for semantic YAML validation, argparse, pytest + coverage, BasedPyright strict, Ruff, `uv_build`.

---

## Source of Truth

- `docs/superpowers/specs/2026-07-10-consumer-standards-control-plane-spec.md` (SPEC-CP01 rev 0.5), especially §§7–12, §17, §19 MS-1–MS-3, and Appendix B.
- `docs/superpowers/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (SPEC-BA02 rev 0.6).
- `docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md`.
- `docs/adr/adr-0023-unified-consumer-standards-control-plane.md`.
- `docs/adr/adr-0024-catalog-scoped-package-version-channels.md`.
- `meta/versioning.md`.
- Implemented BA02 foundation in `src/project_standards/package_contract/` and `tests/package_contract/`.
- `docs/reviews/2026-07-10-consumer-standards-control-plane-core-plan-review.md` (Round 1 remediation contract and approval condition).

## Scope Boundary and Follow-on

This is the second of three implementation layers.

| Layer | Owns | Does not own |
| --- | --- | --- |
| Implemented BA02 foundation | Immutable family/payload/catalog declarations, integrity, graph validation, schemas, installed payload projection | Consumer state or live repository mutation |
| **This plan: control-plane core** | Generic config/catalog/lock models, neutral init, selection, providers, adapters, virtual tree, plan/apply, lifecycle, recovery, CLI, synthetic installed-wheel proof | Reconstructing or activating each current standard package |
| Follow-on package migration/release | Current V2 payloads and options, legacy YAML/artifact migrations, direct-writer conversion, real all-pairs/full composition, dogfood, docs, release evidence | New generic platform semantics |

The core plan must leave the current V1 packages and `.project-standards.yml` behavior usable until the migration plan activates V2. It may add dual-authority detection and the V5 legacy warning, but it must not delete, reinterpret, or silently rewrite legacy state.

### Requirement Allocation

| Requirements | Core-plan evidence | Expected SPEC-CP01 status after this plan |
| --- | --- | --- |
| FR-001–FR-006, IR-001, IR-005–IR-006, DR-001–DR-003 | Tasks 1–5 models, schemas, installed catalog, exact scaffold, and state loading | Passing |
| FR-007–FR-016, IR-003, NFR-001–NFR-004 | Tasks 7 and 9–16 resolver, planner, adapters, lifecycle, executor, and recovery | Passing against generic synthetic packages |
| FR-017 | Task 17 compatibility-wrapper mechanism | Partial until every current package has a V2 payload |
| FR-018–FR-019, FR-025, FR-028, FR-032–FR-034, FR-036 | Tasks 3, 7–8, 14–18 | Passing against source and installed synthetic catalogs |
| FR-026, IR-002, NFR-008 | Tasks 6 and 17 config-edit and CLI contracts | Passing |
| FR-029 | Tasks 9–14 all adapter and virtual-tree mechanism suites | Partial until the real current-package pair/full matrix passes |
| FR-030 | Tasks 1, 6–7 keep payload selection separate from nested package config | Partial until legacy contract selectors migrate |
| FR-031 | Existing approved SPEC-BA02 and foundation evidence | Passing |
| FR-035 | Tasks 8 and 16 provider/executor mechanism and filesystem-spy tests | Partial until every current direct-write provider is converted |
| FR-020–FR-024, FR-027, IR-004, DR-006, NFR-007 | Follow-on package migration/release plan | Not Started except generic mechanisms |
| NFR-005–NFR-006, NFR-009 | Tasks 4, 14, and 18 | Passing for the generic core |

## Plan-Pinned Contracts

These choices resolve implementation details without changing the approved behavior.

1. **One package option shape.** Desired options live only at `standards.STANDARD_ID.config`, matching approved SPEC-BA02 FR-007 and the implemented `PackageOptionSchema.namespace`. No top-level `[config]` compatibility alias is added.
2. **Semantic digests.** Config and effective-option digests are SHA-256 over UTF-8 canonical JSON (`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`) of validated semantic values. Artifact/contribution digests use exact content bytes or the adapter's canonical normalized semantic value as appropriate.
3. **Catalog self-digest.** `project_standards.digest` is SHA-256 over the canonical catalog bytes rendered with that field omitted. Verification removes the field, rerenders, and compares. This avoids a recursive hash while binding every other catalog fact.
4. **Preserving edits without new parser dependencies.** Tool-owned catalog and lock files use purpose-built canonical renderers. User-owned config and shared containers use bounded token/span edits after semantic parsing; they never full-reserialize an existing consumer file. `tomllib`, `json`, and PyYAML validate semantics, while adapter-owned scanners identify the exact byte spans to add, update, or remove.
5. **Linux directory locks.** `fcntl.flock` is taken on an open `.standards/` directory descriptor. No lock file is created or ignored. Read-only commands use `LOCK_SH | LOCK_NB`; config edits, init, repair, and apply use `LOCK_EX | LOCK_NB`.
6. **Trusted provider boundary, not a security sandbox.** Providers load only from integrity-checked selected payload resources, receive immutable JSON-compatible snapshots without a repository path, and return schema-validated data. Before/after repository fingerprints detect an out-of-contract live write and retain the prior lock. Preventing malicious trusted Python code is outside the V1 boundary stated by SPEC-CP01.
7. **Markdown formatter stability.** Managed Markdown blocks include a declared Prettier range exclusion around the bounded block. Adapter tests run the repository's pinned Prettier and require format-then-reconcile to be a no-op; semantic normalization does not erase Markdown syntax distinctions.
8. **No force escape hatch.** Conflicts make the complete plan non-applicable. Apply accepts no flag that chooses precedence or overwrites modified consumer/managed units.
9. **Catalog-major encoding.** TOML stores the catalog major as a quoted canonical decimal string such as `"5"`; CLI arguments parse a positive integer and render it without leading zeros.
10. **Secret handling.** A package-option schema path marked with standard JSON Schema `writeOnly: true` is secret material and therefore invalid in committed desired config. Diagnostics never include configured values or provider output; failed provider stdout/stderr is replaced by a bounded redaction notice. Credential-reference strings remain allowed because the package schema validates their reference syntax, while control-plane output reports only field paths and digests.

## Public Interfaces

```python
from pathlib import Path

from project_standards.control_plane import (
    ReconciliationPlan,
    apply_plan,
    build_plan,
    initialize_control_plane,
    load_control_plane,
)

repository = Path.cwd()
state = load_control_plane(repository)
plan: ReconciliationPlan = build_plan(state)
apply_plan(repository, plan)
```

```bash
project-standards init --catalog 5 --repo .
project-standards standards list --repo . [--json]
project-standards standards show STANDARD_ID --repo . [--json]
project-standards standards enable STANDARD_ID --repo . [--version latest|MAJOR.MINOR]
project-standards standards disable STANDARD_ID --repo .
project-standards standards version STANDARD_ID latest|MAJOR.MINOR --repo .
project-standards reconcile --repo . [--check] [--apply]
  [--allow-major STANDARD_ID@MAJOR]... [--repair-state] [--json]
```

Exit codes are `0` for a successful/no-drift command, `1` for drift, conflict, or an apply/runtime failure, and `2` for usage or invalid/load-boundary input. JSON output contains stable codes and metadata but never artifact content, provider stdout beyond its bound, or secret values.

## Target File Structure

```text
src/project_standards/control_plane/
├── __init__.py
├── adapters/
│   ├── __init__.py
│   ├── base.py
│   ├── editorconfig.py
│   ├── jsonc.py
│   ├── markdown.py
│   ├── registry.py
│   ├── toml.py
│   ├── whole_file.py
│   └── yaml.py
├── bootstrap.py
├── cli.py
├── codec.py
├── config_edit.py
├── diagnostics.py
├── distribution.py
├── executor.py
├── locking.py
├── models.py
├── paths.py
├── planner.py
├── providers.py
├── recovery.py
├── resolution.py
├── schemas.py
├── snapshot.py
└── state.py

src/project_standards/schemas/
├── consumer-catalog.schema.json
├── consumer-config.schema.json
├── consumer-lock.schema.json
├── mutation-plan.schema.json
├── provider-input.schema.json
└── reconciliation-plan.schema.json

tests/control_plane/
├── __init__.py
├── helpers.py
├── test_adapters_*.py
├── test_bootstrap.py
├── test_cli.py
├── test_codec.py
├── test_config_edit.py
├── test_distribution.py
├── test_end_to_end.py
├── test_executor.py
├── test_locking.py
├── test_models.py
├── test_planner.py
├── test_providers.py
├── test_recovery.py
├── test_resolution.py
├── test_scale.py
├── test_schemas.py
└── test_state.py
```

The shared `tests/wheel_helpers.py` prerequisite was added during plan-review remediation. It extracts the repository's test-built pure-Python wheels with stdlib `zipfile`, so Tasks 3, 5, and 18 never invoke `uv pip`, depend on a harness-specific `uv` path, or forward the ambient environment to an installer subprocess.

Also modify `src/project_standards/cli.py`, `src/project_standards/standards_graph/cli.py`, `src/project_standards/package_contract/catalog.py`, `src/project_standards/package_contract/cli.py`, `src/project_standards/package_contract/projection.py`, package-contract tests/goldens, `pyproject.toml` only if package-data declarations require it, `docs/usage.md`, SPEC-CP01 traceability, and handoff/status documents.

---

### Task 1: Control-Plane Diagnostics, Paths, and Strict State Models

**Files:** Create `control_plane/{__init__,diagnostics,paths,models}.py`; create `tests/control_plane/{__init__,test_models}.py`.

- [ ] Write failing tests for strict config/catalog/lock models, invalid/extra keys, package IDs, selectors, catalog majors, digest shapes, duplicate owners, disabled-package lock records, accepted-track separation, forbidden executable/URL values, and secret-value rejection/redaction.
- [ ] Run `uv run pytest tests/control_plane/test_models.py -q`; expect import/collection failure.
- [ ] Implement frozen domain models. The central shapes must include:

```python
type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type VersionSelector = Literal["latest"] | PackageVersion


class DesiredPackage(StrictModel):
    enabled: bool
    version: VersionSelector
    config: dict[str, JsonValue] = Field(default_factory=dict)


class DesiredConfig(StrictModel):
    project_standards: ControlHeader
    standards: dict[KebabId, DesiredPackage] = Field(default_factory=dict)
```

`ControlHeader` contains only `schema_version: Literal["1.0"]` and the canonical catalog-major string. Define equally strict `ConsumerCatalog`, `CentralLock`, `AppliedPackage`, `AcceptedTrack`, `LockedUnit`, and `LockedInput` models with the exact fields required by SPEC-CP01 DR-002–DR-003; every collection validator sorts and rejects duplicate natural keys.

- [ ] Add deterministic finding/action ordering and JSON-safe serialization that omits internal content bytes.
- [ ] Run the focused tests, Ruff, and BasedPyright; expect pass.
- [ ] Commit: `feat(v5): model consumer control-plane state`

### Task 2: Canonical Digests, TOML Codecs, and Generated Schemas

**Files:** Create `control_plane/{codec,schemas}.py`; modify `package_contract/cli.py`; create `tests/control_plane/{test_codec,test_schemas}.py`; add six generated schemas.

- [ ] Write red tests for the plan-pinned digest vectors, canonical config/catalog/lock rendering, parse/render round trips, self-digest verification, stable ordering, UTF-8 errors, and generated-schema drift.
- [ ] Run the two focused modules; expect failure.
- [ ] Implement purpose-built renderers rather than a generic TOML serializer. `render_empty_config`, `render_catalog`, and `render_lock` must emit stable LF-terminated UTF-8 bytes and quote strings through `json.dumps`.
- [ ] Extend `package_contract.catalog.render_consumer_catalog` with the CP01 catalog self-digest and update its golden/tests. Include an independent test that recomputes the hash from bytes with the digest line omitted.
- [ ] Generate and check the six JSON Schemas from the strict models; close every object that is not intentionally keyed by package ID. Register the control-plane generator with the existing `generate-package-schemas` CLI path so one command checks all nine generated schemas without making `package_contract.schemas` import the higher-level control plane.
- [ ] Make the red drift test alter one control-plane schema and assert `standards generate-package-schemas --check` returns `1`; restoring generated bytes must return `0`.
- [ ] Run focused tests and `uv run project-standards standards generate-package-schemas --root . --check`; expect pass.
- [ ] Commit: `feat(v5): define control-plane codecs and schemas`

### Task 3: Installed Distribution Catalog and Payload Access

**Files:** Create `control_plane/distribution.py`; modify package-contract projection and tests; create `tests/control_plane/test_distribution.py`.

- [ ] Write a failing synthetic-wheel test that uses `tests.wheel_helpers.extract_pure_python_wheel`, loads catalog major 5 through `importlib.resources`, validates all payload digests, and proves no network construction.
- [ ] Add red cases for missing catalog projection, tool/catalog major mismatch, newer same-major catalog release, stale payload digest, and unavailable payload.
- [ ] Extend the canonical symlink projection so root `catalogs/*.toml` sources are also installed under `project_standards/catalogs/`; authored catalog bytes remain only at root.
- [ ] Implement `InstalledDistribution` as the only production source for catalog/payload facts. Tests may inject an explicit package repository; normal CLI code may not accept remote or config-selected sources.
- [ ] Run package-contract and distribution tests; expect pass and byte-identical source/wheel facts.
- [ ] Commit: `feat(v5): expose installed control-plane catalogs`

### Task 4: State Detection and Advisory Directory Locking

**Files:** Create `control_plane/{state,locking}.py`; create `tests/control_plane/{test_state,test_locking}.py`.

- [ ] Write state-matrix tests for uninitialized, initialized, incomplete, dual authority, legacy-only, malformed files, tool/catalog mismatch, and newer recorded release.
- [ ] Write multiprocess tests proving concurrent readers succeed; reader/writer and writer/writer contention fail immediately with `CP-BUSY`; process exit releases the directory lock; no lock artifact appears.
- [ ] Implement `ControlPlaneState` and `control_plane_lock(repo, mode)` with repository containment, a resolved `.standards/` directory descriptor, and non-blocking `fcntl.flock`.
- [ ] Ensure every read begins only after acquiring the appropriate lock; do not read a potentially changing file first.
- [ ] Run both focused modules repeatedly (`--count` is not available; use a shell loop of ten pytest invocations); expect stable pass.
- [ ] Commit: `feat(v5): detect and lock consumer state`

### Task 5: Exact Neutral Initialization

**Files:** Create `control_plane/bootstrap.py`; create `tests/control_plane/test_bootstrap.py`; modify top-level CLI dispatch tests.

- [ ] Write red CLI/library tests for exact three-file creation, zero enabled packages, no optional directories, idempotency, legacy refusal, partial-state refusal, symlink/path safety, atomic publication, and cleanup after failure at each pre-publication boundary.
- [ ] Implement `initialize_control_plane(repo, catalog_major)` under an exclusive directory lock. Stage all three bytes before publication; publish `config.toml`, `catalog.toml`, then `lock.toml`; remove only a transient empty `.standards/` created by the failed call.
- [ ] Prove a second init compares semantic/canonical state and changes no bytes.
- [ ] Build a synthetic wheel, extract it through the shared stdlib helper, and assert the initialized tree contains exactly the directory plus three regular files with network construction denied.
- [ ] Run focused and installed-wrapper tests; expect pass.
- [ ] Commit: `feat(v5): initialize the neutral standards plane`

### Task 6: Comment-Preserving Config Inspection and Edits

**Files:** Create `control_plane/config_edit.py` and `control_plane/adapters/{__init__,toml}.py`; create `tests/control_plane/test_config_edit.py`; modify standards CLI dispatch.

- [ ] Write red round-trip fixtures containing comments, alternate quoting, unusual package order, nested config arrays/tables, and unrelated whitespace.
- [ ] Implement the reusable TOML statement/span scanner, then bounded edits for `enable`, `disable`, and `version`: touch only the selected package's `enabled` or `version` span; preserve selector/options on disable; append a new package table deterministically when absent; validate the complete result before atomic replacement.
- [ ] Implement read-only `standards list/show` from catalog plus desired/applied state. Internal/reference-only packages remain visible but cannot be enabled.
- [ ] Prove CLI edits and equivalent manual edits yield identical parsed desired state and reconciliation plans even when their physical TOML differs.
- [ ] Run focused tests plus top-level help/JSON snapshots; expect pass.
- [ ] Commit: `feat(v5): edit desired package state safely`

### Task 7: Catalog-Scoped Package Resolution and Track Transitions

**Files:** Create `control_plane/resolution.py`; create `tests/control_plane/test_resolution.py`.

- [ ] Write table-driven red tests covering exact pins, ordinary `latest`, several candidate majors, matching/mismatched `ID@MAJOR`, retained accepted tracks, disabled/re-enabled packages, unavailable tracks, same-major catalog refresh, promotion normalization, exact-target exit, missing migration/rollback paths, and no downgrade.
- [ ] Implement a pure resolver:

```python
@dataclass(frozen=True, slots=True)
class MajorAuthorization:
    standard_id: str
    target_major: int


@dataclass(frozen=True, slots=True)
class ResolutionRequest:
    desired: DesiredConfig
    catalog: ConsumerCatalog
    previous_lock: CentralLock
    allowed_majors: frozenset[MajorAuthorization]


def resolve_packages(request: ResolutionRequest) -> ResolutionResult: ...
```

- [ ] Validate selected payload options only after resolution by calling that payload's `PackageOptionSchema.resolve_options`; keep `version` and package-owned `contract_version` independent.
- [ ] Return explicit accepted-track create/replace/remove transitions; never mutate config or lock inside the resolver.
- [ ] Run randomized input-order/property-style tests for 100 permutations; expect one result fingerprint.
- [ ] Commit: `feat(v5): resolve catalog-scoped package versions`

### Task 8: Referenced Inputs and Version-Selected Provider Boundary

**Files:** Create `control_plane/providers.py`; create `tests/control_plane/test_providers.py` and provider fixtures.

- [ ] Write red tests for preferred/conventional extension paths, missing input, traversal, absolute path, symlink escape, package-namespace overlap, planned-output alias, digest change, and disable preservation.
- [ ] Write provider tests for exact payload/version selection, declared phase/effect/operation, resource and JSON-schema bounds, immutable snapshot input, bounded stdout/stderr, typed finding/content/mutation-plan output, unsupported effects, exceptions, and observed live writes.
- [ ] Load `payload:RESOURCE#SYMBOL` only from the selected integrity-checked payload. Pass deep-frozen JSON-compatible values and declared resource bytes; never pass the live repository path.
- [ ] Fingerprint declared/live repository paths before and after execution. Emit `CP-PROVIDER-INTEGRITY` and stop if any live path changes; retain prior lock and execute no later provider/action.
- [ ] Run with socket construction monkeypatched and filesystem mutation spies; expect no network and no supported provider-side write.
- [ ] Commit: `feat(v5): bound package provider execution`

### Task 9: Adapter Protocol, Snapshots, and Whole-File Artifacts

**Files:** Create `control_plane/snapshot.py` and `adapters/{base,registry,whole_file}.py`; extend `adapters/__init__.py`; create `tests/control_plane/test_adapters_whole_file.py`.

- [ ] Define adapter contract tests for create, adopt-equal, update, no-op, preserve, remove, malformed input, duplicate identity, consumer conflict, package overlap, modified managed unit, and concurrent precondition failure.
- [ ] Implement `RepositorySnapshot` that reads each declared target once, records exact bytes/mode/symlink state/digest, and rejects all repository escapes before content reads.
- [ ] Implement the protocol:

```python
class DocumentAdapter(Protocol):
    def inspect(self, content: bytes, scopes: tuple[str, ...]) -> AdapterState: ...
    def render(self, state: AdapterState, changes: tuple[UnitChange, ...]) -> bytes: ...
```

- [ ] Implement whole-file semantics, including managed versus create-only, exact mode tracking, modified-content conflict, and container deletion only when the lock proves platform creation and no durable content remains.
- [ ] Run focused adapter tests and strict checks; expect pass.
- [ ] Commit: `feat(v5): add snapshot and adapter boundaries`

### Task 10: Round-Trip TOML Adapter

**Files:** Extend `adapters/toml.py`; create `tests/control_plane/test_adapters_toml.py` and fixtures.

- [ ] Add fixtures for key/table scopes, dotted and quoted keys, multiline arrays/strings, comments, unusual ordering, CRLF rejection or preservation decision, duplicate semantic keys, and unrelated bytes.
- [ ] Implement a TOML statement scanner that tracks strings/bracket depth and records exact header/assignment spans. Use `tomllib` for semantic validation and normalized values; splice only owned spans.
- [ ] Append new keys/tables at the approved parent/end placement point in canonical contribution order. Removing a final owned key must preserve comments and must not delete a consumer-owned table header.
- [ ] Assert every unowned byte slice is identical before/after and a second render is byte-identical.
- [ ] Commit: `feat(v5): compose semantic TOML units`

### Task 11: Round-Trip JSON and JSONC Adapter

**Files:** Create `adapters/jsonc.py`; create `tests/control_plane/test_adapters_jsonc.py` and fixtures.

- [ ] Add fixtures for object keys, set entries, keyed-set task/hook entries, line/block comments, trailing commas, alternate spacing, duplicate identities, escaped strings, and malformed documents.
- [ ] Implement a JSONC lexer that recognizes strings/comments/punctuation and derives exact member/element spans. Parse a comment-stripped semantic view with `json`; retain original tokens for bounded splices.
- [ ] Implement `key:`, `set:`, and `keyed-set:` scopes from the normalized BA02 selectors. Add/remove commas without reformatting siblings; preserve existing item order and append new set entries canonically.
- [ ] Prove VS Code settings/tasks/extensions and harness hook examples preserve all consumer comments and bytes outside changed spans.
- [ ] Commit: `feat(v5): compose JSONC semantic units`

### Task 12: Round-Trip YAML Adapter

**Files:** Create `adapters/yaml.py`; create `tests/control_plane/test_adapters_yaml.py` and fixtures.

- [ ] Add fixtures for mappings, keyed sequences, comments, quotes, anchors/aliases, document markers, workflow expressions, duplicate keys/identities, and malformed YAML.
- [ ] Use `yaml.compose` node marks to identify owned mapping/sequence spans and `yaml.safe_load` for normalized values. Reject ambiguous duplicate keys, merge-key ownership, or a requested edit whose node marks cannot prove a bounded splice.
- [ ] Insert new mapping entries at the end of their parent with detected indentation; preserve all unowned bytes. Whole workflow documents continue to use the whole-file adapter unless the payload declares a supported semantic scope.
- [ ] Prove GitHub workflow expressions and unrelated comments remain byte-identical.
- [ ] Commit: `feat(v5): compose bounded YAML units`

### Task 13: EditorConfig and Formatter-Stable Markdown Adapters

**Files:** Create `adapters/{editorconfig,markdown}.py`; create both focused test modules and fixtures; modify `docs/handoff/conventions.md`.

- [ ] Implement EditorConfig section/property span indexing, case/whitespace normalization, duplicate detection, shared-property identity, append placement, and bounded removal.
- [ ] Implement Markdown block IDs with exact begin/end markers plus Prettier range-exclusion markers. Reject inline, nested, duplicate, orphaned, or cleanup-ambiguous marker layouts.
- [ ] Cover shared last-reference removal, consumer property conflicts, multiple managed blocks, unrelated prose/fences, CRLF, and end-of-file placement.
- [ ] Run pinned Prettier over managed Markdown fixtures, then reconcile; expect a no-op and identical normalized digest.
- [ ] Record the verified Prettier range-exclusion pattern in `docs/handoff/conventions.md` when the adapter lands; distinguish it from the existing single-node `prettier-ignore` convention.
- [ ] Commit: `feat(v5): compose editorconfig and markdown units`

### Task 14: Complete Virtual-Tree Planner

**Files:** Create `control_plane/planner.py`; create `tests/control_plane/test_planner.py`; extend helpers/full synthetic fixtures.

- [ ] Write red aggregate tests for create, adopt-equal, semantic merge, update, repair, remove, preserve, no-op, every conflict class, shared references, provider output, extension inputs, package-local outputs, and argument/discovery permutations.
- [ ] Implement one pipeline in approved order: resolve; snapshot; invoke plan providers; normalize current/desired/locked units; detect all overlaps/conflicts; classify; render every target in memory; emit one final action per target and unit-level provenance.
- [ ] The immutable `ReconciliationPlan` must carry public JSON-safe facts, internal proposed bytes, exact whole-file preconditions, resolution/track transitions, verification requests, and a proposed next lock. It is applicable only when every finding is non-blocking.
- [ ] Prove any conflict blocks every target before the first executor call and canonical order affects placement only, never value selection.
- [ ] Run 100 randomized package/filesystem discovery orders; expect byte-identical plan JSON and proposed bytes.
- [ ] Commit: `feat(v5): plan complete repository reconciliation`

### Task 15: Central Lock, Disable/Re-enable, and Package-Local Lifecycle

**Files:** Extend `models.py`, `codec.py`, and `planner.py`; create `tests/control_plane/test_lifecycle.py`.

- [ ] Write lifecycle sequences for enable/apply, compatible update, disable, re-enable, shared-owner removal, last-reference removal, create-only preservation, modified/undeclared package-local content, namespace pruning, and accepted-track normalization.
- [ ] Record each unit's target, adapter, normalized scope, owners/shared references, selected package/version, provenance, semantic digest, policy, mode, and container-creation evidence. Record referenced inputs separately without managed owners.
- [ ] Ensure disabled packages have no applied record after successful removal while their accepted tracks persist. Re-enable `latest` must consult the track and fail closed when unavailable.
- [ ] Reject duplicate package locks and undeclared entries below `.standards/packages/STANDARD_ID/`; prune only an empty namespace whose declared content was safely removed.
- [ ] Run lock round-trip, drift, and lifecycle tests; expect pass.
- [ ] Commit: `feat(v5): converge central package lifecycle state`

### Task 16: Executor-Only Apply, Verification, and Recovery

**Files:** Create `control_plane/{executor,recovery}.py`; create `tests/control_plane/{test_executor,test_recovery}.py`.

- [ ] Write fault-injection tests at every stage/write/verify/lock boundary, including destination races, symlink swaps, permission failures, interruption, provider verification failure, and stale plan reuse.
- [ ] Under one exclusive directory lock, recompute the plan or compare its complete input fingerprint, recheck every target precondition, stage all proposed bytes beside destinations, publish atomic replacements, run read-only verification providers, and replace `lock.toml` last.
- [ ] Preserve the previous lock on every failure. Return the exact successfully published action IDs so the next read-only plan classifies the partial live transition as repair/conflict rather than success.
- [ ] Implement sanctioned incomplete-state recovery: missing config refuses inference; missing catalog regenerates only from the matching installed distribution; missing lock produces an evidence-backed plan with no accepted tracks and requires `--repair-state --apply` plus any candidate reauthorization.
- [ ] Prove a successful second apply is a no-op and no automatic retry occurs.
- [ ] Commit: `feat(v5): apply and recover control-plane plans`

### Task 17: CLI, Validation, and V5 Adopt Compatibility Wrapper

**Files:** Create `control_plane/cli.py`; modify top-level and standards CLI dispatch; modify `docs/usage.md`; create `tests/control_plane/test_cli.py` and installed-wrapper tests.

- [ ] Add help and human/JSON snapshots for init, list/show/enable/disable/version, reconcile plan/check/apply, `--allow-major`, and `--repair-state`, including the 0/1/2 exit contract.
- [ ] Add control-plane drift to top-level `validate` when unified state exists. Legacy-only config remains read-only with a migration warning; dual authority is an error. Per-package legacy-config adapters remain deferred.
- [ ] Refactor `adopt` into a V5 wrapper path that initializes if needed, updates desired state, builds a plan, and applies only under the existing explicit mutating invocation. Emit the documented deprecation notice. Keep the legacy V1 path until real V2 package activation in the follow-on plan.
- [ ] Give top-level `project-standards list` the same V5 deprecation notice in this task. `project-standards standards list` is the supported complete catalog inventory; the legacy top-level command continues listing only V1 packaged-adoption artifacts until the follow-on activates real V2 packages.
- [ ] Prove wrapper and explicit init/edit/reconcile yield identical state for a synthetic V2 package, and prove no current package silently switches runtime paths yet.
- [ ] Run all CLI, existing adopt, validation, and wrapper tests; expect pass.
- [ ] Commit: `feat(v5): expose consumer reconciliation commands`

### Task 18: Installed-Wheel, Determinism, Scale, and Core Closeout

**Files:** Create `tests/control_plane/{test_end_to_end,test_scale}.py`; modify SPEC-CP01 traceability, status/handoff docs, and changelog.

- [ ] Build a synthetic source distribution/wheel containing default, retained, candidate, reference-only, and internal packages; extract it through `tests.wheel_helpers.extract_pure_python_wheel`; deny network; initialize; enable; plan; apply; validate; update; disable; re-enable; and recover an interrupted apply.
- [ ] Run every adapter in one combined virtual tree and assert the second reconciliation is a byte-level no-op. Run 100 discovery/config order permutations and compare config/catalog/lock/plan bytes.
- [ ] Add an explicit `performance` test for 100 packages and 1,000 artifacts/contributions completing within five seconds on the normal Linux CI runner.
- [ ] Confirm the existing unscoped `uv run pytest -m performance` workflow step discovers the new control-plane scale test; no `.github/workflows/check.yml` edit is expected.
- [ ] Add an architecture test that injects a previously unknown package using only declarations and asserts no shared source file contains that package ID.
- [ ] Update SPEC-CP01 §17.3 conservatively: mark only requirements proven by fresh core evidence; leave real-package migration/composition/provider conversion items Partial or Not Started.
- [ ] Run an inline implementation review, fix Important-or-higher findings, then run the full verification gate below.
- [ ] Commit: `docs(v5): close consumer control-plane core`

## Verification Gates

Run fail-fast in this order:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest -m 'not performance'
uv run coverage report
uv run pytest -m performance tests/control_plane/test_scale.py
uv run pip-audit
npm ci
uv run pytest tests/coherence
npx prettier --check .
npx markdownlint-cli2 '**/*.md'
uv run project-standards validate --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run project-standards standards validate-graph --root . --require-all-manifests --json
uv run project-standards standards validate-packages \
  --root tests/fixtures/package_contract/valid/full \
  --json
uv run project-standards standards generate-package-schemas --root . --check
TOOL_RELEASE="$(uv run python -c 'from project_standards._version import package_version; print(package_version())')"
uv run project-standards standards render-consumer-catalog \
  --root tests/fixtures/package_contract/valid/full \
  --catalog-major 5 \
  --output expected/catalog.toml \
  --tool-release "$TOOL_RELEASE" \
  --check
uv run project-standards standards sync-payload-projection --root . --check
uv run project-standards agent-handoff validate --repo .
uv run project-standards agent-handoff drift-check --repo .
git diff --check
```

Expected results:

- All source tests pass at or above the repository branch-coverage floor.
- The explicit scale gate passes below five seconds.
- The synthetic installed wheel completes every operation offline.
- Generated schemas, catalog, and installed projection are fresh.
- Existing V1 adoption and validators remain green.
- Documentation, handoff, formatting, and coherence gates pass.

## Plan Completion Criteria

- Plain init creates exactly `.standards/config.toml`, `catalog.toml`, and `lock.toml`, enabling no package.
- Generic package resolution implements exact/default/candidate/accepted-track/promotion semantics without package-ID branches.
- All declared adapters preserve unowned bytes and produce deterministic virtual-tree output.
- Providers cannot supply entrypoints through config and cannot perform a supported direct repository write.
- Reconciliation planning/checking/validation is read-only; explicit apply is executor-only and lock-last.
- Disable/re-enable, shared references, package-local state, extension inputs, and accepted tracks follow the approved lifecycle.
- Missing-state and interrupted-apply recovery fail closed and preserve user-owned config and the previous lock.
- Human/JSON CLI contracts, installed-wheel offline proof, determinism, concurrency, path safety, and scale gates pass.
- SPEC-CP01 traceability distinguishes mechanism-complete core requirements from deferred real-package compatibility work.
- The working tree contains no unintended changes, especially no rewrite of the pre-existing user task in `docs/TODO.md`.
