# Standard Bundle Authoring V2 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implemented inline on `testing` (`4e507d6` through the foundation closeout commit); the 1,693-test final gate passes at 93% branch coverage. The unchecked procedural boxes below are retained as the approved execution script, not as an open-work ledger.

**Goal:** Implement SPEC-BA02 MS-1 and the declaration-only foundation of MS-2: strict versioned-package models, generated schemas, integrity and discovery validation, catalog-source validation, generic graph checks, authoring CLI commands, and byte-identical installed payload projection.

**Architecture:** Add a new `project_standards.package_contract` boundary beside the legacy V1 manifest/graph code. It loads immutable family, payload, and catalog declarations into strict Pydantic models; validates complete payload inventories and cross-package graph invariants without executing providers; and emits stable structured findings. Canonical payload bytes remain under `standards/{id}/versions/{version}/`. A checked-in file-symlink projection under `src/project_standards/payloads/` gives `uv_build` the required wheel path without creating a second editable payload tree. The legacy V1 runtime remains unchanged until the later migration plan activates V2.

**Tech Stack:** Python 3.14, Pydantic 2, stdlib `tomllib`/`hashlib`/`pathlib`/`importlib.resources`, JSON Schema Draft 2020-12, `uv_build`, argparse, pytest + coverage, BasedPyright strict, Ruff.

---

## Source of Truth

- `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md` (SPEC-BA02), especially MS-1 and MS-2.
- `docs/specs/2026-07-10-consumer-standards-control-plane-spec.md` (SPEC-CP01), for the consumer-catalog fields that authoring must supply.
- `docs/superpowers/specs/2026-07-10-root-artifact-ownership-semantic-composition-design.md`.
- `docs/adr/adr-0023-unified-consumer-standards-control-plane.md`.
- `docs/adr/adr-0024-catalog-scoped-package-version-channels.md`.
- `meta/versioning.md`.

## Scope Boundary and Follow-on Plans

This is the first of three executable plans. Keeping the boundaries explicit prevents a package-authoring parser from silently becoming a live-repository mutation engine.

| Plan | Owns | Does not own |
| --- | --- | --- |
| **This plan: BA02 foundation** | Family/payload/catalog declarations, schemas, inventory/digests, graph invariants, installed payload projection, authoring diagnostics | Consumer `.standards/` state, version resolution, live-file parsing/mutation, provider execution |
| **Follow-on: control-plane core** | Neutral init, config/catalog/lock, resolution, virtual tree, adapters, planner/executor, provider sandbox, recovery | Reconstruction of every current package |
| **Follow-on: V5 package migration and release** | Current package payloads, legacy migrations, pairwise/full composition, dogfood, release evidence | New platform semantics not approved by the two specs |

This plan implements the authoring/declaration portions of BA02 FR-001–FR-25 and FR-032–FR-034. It supplies reusable primitives for FR-026–FR-031 but does not claim those documentation, current-package, dogfood, migration-activation, or publication-workflow requirements complete. Provider declarations are validated here; provider execution and filesystem/network spies belong to the control-plane core plan, so FR-014–FR-016 remain `Partial` until that plan passes.

### Requirement Allocation

| Requirements | This plan's evidence | Expected BA02 status at close |
| --- | --- | --- |
| FR-001–FR-008, IR-001–IR-003, DR-001–DR-003 | Tasks 2–3 family/payload/options models and fixtures | Passing |
| FR-009–FR-013, DR-004 | Task 4 resource/output/selector declarations and graph fixtures | Passing for declaration layer; runtime preservation remains control-plane work |
| FR-014–FR-016, IR-005, DR-005 | Tasks 5 and 10 bounds/phase/effect/entrypoint validation | Partial until provider execution and spies pass |
| FR-017–FR-019, DR-006 | Tasks 5 and 10 extension/migration declarations and reachability | Passing for authoring contract; live migration execution remains later work |
| FR-020–FR-021, DR-002 | Task 6 complete inventory and independent digest oracle | Passing |
| FR-022–FR-023, IR-004, IR-006, DR-007 | Task 7 catalog validation and consumer-catalog facts | Passing |
| FR-024–FR-025 | Task 8 released-baseline and catalog-diff classification | Passing |
| FR-026–FR-031 | Follow-on V5 package migration/release plan | Not Started, except reusable declaration primitives |
| FR-032 | Task 11 generated schemas and drift tests | Passing |
| FR-033 | Tasks 9–10 synthetic-package and architecture tests | Passing for authoring core; rechecked in control-plane core |
| FR-034, IR-007, DR-008 | Task 13 source/sdist/wheel parity | Passing for the projection mechanism with a synthetic payload; rechecked against every real payload in the V5 migration plan |
| NFR-001, NFR-003, NFR-004, NFR-007–NFR-009 | Tasks 1, 6–11, and 14 | Passing for authoring layer |
| NFR-002, NFR-005–NFR-006 | Task 14 offline discovery plus follow-on provider/adapter execution suites | Partial |

## Global Constraints

- **TDD throughout.** Every behavior task starts with one focused failing test, proves the intended failure, implements the minimum complete behavior, and reruns the focused test before the wider package suite.
- **No V2 activation in this plan.** Do not replace current V1 `standard.toml`, `adopt.toml`, `registry.json`, bundles, config, or CLI behavior. V1 and V2 code may coexist only as separate implementation namespaces during development; no normal runtime path may merge their facts.
- **No package-ID branches.** Shared code dispatches from model data and enums. Tests include a synthetic package unknown to this repository.
- **Strict models.** Every contract model uses `extra="forbid"`; identifiers, versions, digests, endpoints, paths, and enums are constrained types rather than post-hoc strings.
- **Safe paths.** Reject absolute paths, `..`, backslashes, Windows drive prefixes, null bytes, symlink escapes, non-regular files, and case-colliding normalized paths before reading payload content.
- **Deterministic output.** Sort by normalized package ID, parsed package version, identity, and path. Never depend on filesystem enumeration, TOML declaration, or request order.
- **Stable diagnostics.** Every finding includes `code`, `severity`, `standard_id`, `version`, `path`, `identity`, `message`, and `hint`. Do not include payload content in findings.
- **Schema drift is release-blocking.** Generated schemas are checked in and byte-compared to model output.
- **Canonical payload authority.** Only `standards/{id}/versions/{version}/` contains authored payload files. `src/project_standards/payloads/` may contain directories and relative file symlinks only; parity tests reject regular files there.
- **Commits are narrow.** Use `test(v5):`, `feat(v5):`, and `docs(v5):` prefixes. Do not push.

## Public Interfaces

```python
from pathlib import Path

from project_standards.package_contract import (
    PackageRepository,
    build_package_repository,
    validate_package_repository,
)

repository: PackageRepository = build_package_repository(Path.cwd())
findings = validate_package_repository(repository)
```

```bash
project-standards standards validate-packages --root .
project-standards standards validate-packages --root . --json
project-standards standards render-consumer-catalog --root . --catalog-major 5 --output PATH
project-standards standards render-consumer-catalog --root . --catalog-major 5 --output PATH --check
project-standards standards sync-payload-projection --root . --check
project-standards standards generate-package-schemas --root . --check
```

Exit codes remain `0` for success, `1` for contract findings or stale generated output, and `2` for invocation/load-boundary errors.

## Target File Structure

Create the following new files and directories. `src/project_standards/schemas/` already exists; add only the three named V2 schema files beside its V1 contents.

```text
src/project_standards/package_contract/
├── __init__.py
├── catalog.py
├── cli.py
├── diagnostics.py
├── discovery.py
├── family.py
├── graph.py
├── integrity.py
├── paths.py
├── payload.py
├── projection.py
├── release.py
├── repository.py
└── schemas.py

src/project_standards/schemas/  # existing directory
├── standard-family.schema.json
├── standard-payload.schema.json
└── standards-catalog-source.schema.json

tests/package_contract/
├── __init__.py
├── helpers.py
├── test_catalog.py
├── test_cli.py
├── test_diagnostics.py
├── test_discovery.py
├── test_family.py
├── test_graph.py
├── test_integrity.py
├── test_payload.py
├── test_projection.py
├── test_release.py
├── test_repository.py
└── test_schemas.py

tests/fixtures/package_contract/
├── invalid/
└── valid/
```

Modify:

- `src/project_standards/cli.py` — dispatch the new authoring commands.
- `src/project_standards/standards_graph/cli.py` — advertise and dispatch V2 authoring commands without changing V1 commands.
- `.github/workflows/validate-standards-graph.yml` — run V2 authoring validation and release classification when V2 payloads exist.
- `pyproject.toml` — include canonical `standards/**` and `catalogs/**` in sdists when the projection is introduced.
- `uv.lock` — only if dependency metadata changes; this plan expects no new runtime dependency.
- `.gitignore` — ignore built distributions used by installed-wheel tests if the existing rules do not already cover them.
- `docs/handoff/specs-plans.md` — track plan execution status.

---

### Task 1: Contract Diagnostics and Safe Primitives

**Files:**

- Create: `src/project_standards/package_contract/__init__.py`
- Create: `src/project_standards/package_contract/diagnostics.py`
- Create: `src/project_standards/package_contract/paths.py`
- Create: `tests/package_contract/__init__.py`
- Create: `tests/package_contract/test_diagnostics.py`
- Create: `tests/package_contract/test_paths.py`

- [ ] Write tests for stable finding ordering/JSON shape and for every unsafe-path class.
- [ ] Run `uv run pytest tests/package_contract/test_diagnostics.py tests/package_contract/test_paths.py -q`; expect collection/import failure.
- [ ] Implement immutable findings, the package-load exception boundary, constrained IDs/versions/digests, and repository/payload path normalizers.

Core shapes:

```python
@dataclass(frozen=True, slots=True)
class PackageFinding:
    code: str
    severity: Literal["error", "warning"]
    standard_id: str
    version: str
    path: str
    identity: str
    message: str
    hint: str


class PackageContractError(ValueError):
    """One safe boundary for TOML, JSON, UTF-8, schema, path, and I/O failures."""
```

`PackageVersion` accepts exact `MAJOR.MINOR` only and exposes numeric sort components. `Sha256Digest` accepts lowercase `sha256:` plus exactly 64 lowercase hex digits. Safe paths are normalized POSIX relative paths and retain their original spelling for diagnostics.

- [ ] Add table tests proving diagnostic ordering does not depend on input order.
- [ ] Run the focused tests; expect all pass.
- [ ] Run `uv run ruff check src/project_standards/package_contract tests/package_contract` and `uv run basedpyright`; expect pass.
- [ ] Commit: `feat(v5): add package contract primitives`

### Task 2: Strict Package-Family Model and Loader

**Files:**

- Create: `src/project_standards/package_contract/family.py`
- Create: `tests/package_contract/test_family.py`
- Create: `tests/fixtures/package_contract/valid/minimal/standards/demo/README.md`
- Create: `tests/fixtures/package_contract/valid/minimal/standards/demo/standard.toml`
- Create invalid family fixtures under `tests/fixtures/package_contract/invalid/family/`

- [ ] Write a minimal valid family test plus parametrized failures for missing/extra keys, bad schema version, directory-ID mismatch, duplicate versions, unsafe payload paths, invalid digests, and a forbidden channel field such as `latest`.
- [ ] Run `uv run pytest tests/package_contract/test_family.py -q`; expect import failure.
- [ ] Implement the exact family model:

```python
class FamilyManifest(StrictModel):
    schema_version: Literal["2.0"]
    standard: StandardIdentity
    versions: list[VersionIndexEntry] = Field(min_length=1)


class VersionIndexEntry(StrictModel):
    version: PackageVersion
    payload: SafeRelativePath
    digest: Sha256Digest
```

The loader must wrap `TOMLDecodeError`, `UnicodeDecodeError`, `OSError`, and `ValidationError` as `PackageContractError`, then validate directory identity and exact `versions/{version}/payload.toml` targeting.

- [ ] Prove declaration-order permutations load to the same normalized representation.
- [ ] Run focused tests and strict type/lint checks; expect pass.
- [ ] Commit: `feat(v5): model versioned package families`

### Task 3: Payload Identity, Options, Capabilities, and Relations

**Files:**

- Create: `src/project_standards/package_contract/payload.py`
- Create: `tests/package_contract/test_payload.py`
- Extend valid/invalid payload fixtures.

- [ ] Write red tests for exact ID/version matching, availability enum, capability lists, companion/extends/conflicts relations, forbidden `requires`, and forbidden legacy adoption values.
- [ ] Add package-option schema tests: Draft 2020-12, closed object, root namespace `standards.<id>.config`, unknown-option rejection, deterministic defaults, and ordinary `contract_version` behavior.
- [ ] Run the focused module; expect failure.
- [ ] Implement the strict payload root and option-schema loader. Preserve raw option-schema bytes and parsed JSON separately so integrity uses source bytes while validation uses the parsed object.

```python
class PayloadManifest(StrictModel):
    schema_version: Literal["1.0"]
    payload: PayloadIdentity
    config: ConfigDeclaration
    capabilities: CapabilityDeclaration
    relations: RelationDeclaration = Field(default_factory=RelationDeclaration)
    resources: list[ResourceDeclaration]
    artifacts: list[WholeArtifactDeclaration] = Field(default_factory=list)
    contributions: list[ContributionDeclaration] = Field(default_factory=list)
    providers: list[ProviderDeclaration] = Field(default_factory=list)
    extensions: list[ExtensionDeclaration] = Field(default_factory=list)
    migrations: list[MigrationDeclaration] = Field(default_factory=list)
    legacy_signatures: list[LegacySignatureDeclaration] = Field(default_factory=list)
```

The root field names above match the normative TOML tables exactly: `[payload]`, `[config]`, and `[[legacy_signatures]]`. Nested declarations are expanded in Tasks 3–5 rather than inferred from this abbreviated root sketch.

- [ ] Verify no model contains catalog roles or a `latest` field.
- [ ] Run focused tests and strict checks; expect pass.
- [ ] Commit: `feat(v5): model package payload identity and options`

### Task 4: Resources, Whole Artifacts, and Semantic Contributions

**Files:**

- Modify: `src/project_standards/package_contract/payload.py`
- Create: `tests/package_contract/test_payload_outputs.py`
- Extend output declaration fixtures.

- [ ] Write failing tests for stable identity uniqueness, source/digest pairing, target safety, managed/create-only policy, exclusive whole-file ownership, optional POSIX mode, and source/provider XOR.
- [ ] Cover every V1 adapter/selector vocabulary: whole file; TOML key/table; JSON/JSONC key and stable-set entry; YAML mapping and stable keyed entry; EditorConfig section/property; delimiter-bounded Markdown block.
- [ ] Add static scope normalization tests, including same-scope duplicates, parent/child overlap, target/adapter mismatch, and invalid delimiter identities.
- [ ] Implement typed declaration unions discriminated by adapter and selector kind. Normalization returns a stable `SemanticAddress(target, adapter, scope)` used by graph validation; it does not read or mutate consumer files.
- [ ] Add shared-identity tests requiring identical normalized adapter, scope, source value, and digest for all references.
- [ ] Run `uv run pytest tests/package_contract/test_payload_outputs.py -q`; expect pass.
- [ ] Commit: `feat(v5): model package output ownership`

### Task 5: Providers, Referenced Extensions, and Migrations

**Files:**

- Modify: `src/project_standards/package_contract/payload.py`
- Create: `tests/package_contract/test_payload_execution_contracts.py`
- Extend provider/extension/migration fixtures.

- [ ] Write red provider tests for stable ID, generic operation, kind, phase, allowed effect, payload-local entrypoint, input/output schemas, declared resources, and phase/effect incompatibilities.
- [ ] Write referenced-extension tests for option binding, content-type allowlist, repository-relative path policy, preferred `.standards/extensions/{id}/` location, and output/package-namespace overlap rejection.
- [ ] Write migration tests for `package:VERSION` and registered `legacy:STATE` endpoints, automatic/manual mode, provider/instruction XOR, reversibility, affected identity completeness, and exact legacy signatures.
- [ ] Include the exact Agent Handoff legacy Markdown, TOML, and YAML marker forms from SPEC-BA02 as fixtures. Do not reinterpret them as V2 delimiters.
- [ ] Implement declarations and local consistency checks. Execution entrypoints remain opaque payload-relative resource references in this plan.
- [ ] Run focused tests; expect pass.
- [ ] Commit: `feat(v5): model providers extensions and migrations`

### Task 6: Complete Inventory and Canonical Payload Digest

**Files:**

- Create: `src/project_standards/package_contract/integrity.py`
- Create: `tests/package_contract/test_integrity.py`
- Add integrity fixtures.

- [ ] Write failing tests for missing declared files, undeclared regular files, duplicate declarations, digest mismatch, media mismatch, symlink files, symlink directories, symlink escape, FIFO/non-regular entries, and case-colliding paths.
- [ ] Add an independent test-side digest implementation from the normative algorithm rather than importing production helpers.
- [ ] Implement streaming SHA-256 and canonical aggregate digest:

```text
entries = for payload.toml and every other declared file:
    UTF8(normalized_path) + NUL + ASCII("sha256:" + lowercase_hex_digest) + LF

aggregate = "sha256:" + lowercase_hex(SHA256(concatenate(
    entries sorted together by normalized UTF-8 path bytes
)))
```

Use the exact separator, digest form, ordering, and golden vector defined in SPEC-BA02 §9. The independent test oracle must reproduce the spec's two-file aggregate `sha256:eb5608592b65f5e627a592e1af5db67222a43fb0fadd6002f77f5cda3f10943a`. If the normative prose and vector disagree, stop and amend the approved spec before implementation.

- [ ] Test a one-byte change in every payload file class and prove failure occurs before graph/provider work.
- [ ] Run focused tests; expect pass.
- [ ] Commit: `feat(v5): validate immutable payload inventories`

### Task 7: Repository Catalog Source and Channel Invariants

**Files:**

- Create: `src/project_standards/package_contract/catalog.py`
- Create: `tests/package_contract/test_catalog.py`
- Add `catalogs/` fixtures under the package-contract fixture repositories.

- [ ] Write red tests for schema version, catalog-major match, exact family version/digest match, channel role enum, and unknown package/version rejection.
- [ ] Add invariant cases: exactly one default per ordinary consumer package; same-major compatible default advancement; retained/candidate coexistence; candidate-major separation; reference-only/internal availability agreement; and no implicit default change.
- [ ] Implement strict catalog models and cross-reference validation against loaded families/payloads.

```python
class CatalogSource(StrictModel):
    schema_version: Literal["1.0"]
    catalog_major: int = Field(ge=1)
    packages: list[CatalogPackageEntry]
```

- [ ] Implement deterministic generation of the package/version/channel/digest portion required by SPEC-CP01 `.standards/catalog.toml`. Do not generate consumer enabled state or locks.
- [ ] Require `--output PATH`; there is no repository-default consumer-catalog destination. Write mode atomically replaces that caller-selected file. `--check` is read-only and compares regenerated bytes with that same path.
- [ ] Track a golden output only at `tests/fixtures/package_contract/valid/full/expected/catalog.toml`. Production authoring inputs remain `catalogs/{catalog-major}.toml`; the control-plane runtime later owns each consumer's committed `.standards/catalog.toml`.
- [ ] Prove repeated rendering and randomized input order produce byte-identical TOML.
- [ ] Commit: `feat(v5): validate catalog scoped package channels`

### Task 8: Released-Payload Immutability and Catalog-Diff Classification

**Files:**

- Create: `src/project_standards/package_contract/release.py`
- Create: `tests/package_contract/test_release.py`
- Modify: `.github/workflows/validate-standards-graph.yml`
- Modify: `tests/test_standards_graph_workflow.py`

- [ ] Write red tests that compare a working repository to a released-tag baseline and reject payload byte mutation, payload deletion, digest replacement, ordinary default promotion across package majors, and candidate promotion without the ADR 0024 tool/catalog-major change.
- [ ] Add accepted cases for a new unreleased payload, same-major compatible default advancement, retained history, new non-default candidate major, and candidate promotion in a new catalog major.
- [ ] Implement a pure `classify_catalog_diff(previous, current, tool_versions)` API. Keep Git access in a thin boundary that invokes `git` with an argument vector (never a shell), validates the ref, and loads only declared catalog/family/payload paths from the baseline tree.
- [ ] Return stable findings and a release classification (`patch`, `minor`, `major`, or `forbidden`) rather than changing versions or catalogs.
- [ ] Add workflow coverage that supplies the prior released catalog tag when one exists and skips the comparison only when there is provably no released V2 baseline.
- [ ] Run `uv run pytest tests/package_contract/test_release.py tests/test_standards_graph_workflow.py -q`; expect pass.
- [ ] Commit: `feat(v5): enforce released package immutability`

### Task 9: Safe Discovery and Package Repository Model

**Files:**

- Create: `src/project_standards/package_contract/discovery.py`
- Create: `src/project_standards/package_contract/repository.py`
- Create: `tests/package_contract/helpers.py`
- Create: `tests/package_contract/test_discovery.py`
- Create: `tests/package_contract/test_repository.py`

- [ ] Write failing repository-fixture tests for deterministic discovery, missing baseline files, duplicate normalized IDs, malformed UTF-8/TOML/JSON, family/payload mismatch, and error aggregation across independent packages.
- [ ] Require at least one V2 family for ordinary validation. An empty discovery is `PC-NO-FAMILIES`, not a vacuous success; transition gates target the full synthetic fixture until the follow-on migration plan introduces the first repository family.
- [ ] Implement `build_package_repository(root, *, catalog_major=None)` as a load-only boundary. It may read only V2 family indexes, their indexed payloads, their declared files, and the selected catalog source.
- [ ] During the transition, require an explicit V2 family allowlist or `schema_version = "2.0"` preamble probe. Record the probe as a temporary migration seam; do not parse V1 manifest facts into V2 nodes.
- [ ] Ensure one broken payload yields a structured load finding without masking independent package findings, except unsafe root/path failures which stop immediately.
- [ ] Run focused tests; expect pass.
- [ ] Commit: `feat(v5): discover versioned package repositories`

### Task 10: Cross-Payload Graph Validation

**Files:**

- Create: `src/project_standards/package_contract/graph.py`
- Create: `tests/package_contract/test_graph.py`

- [ ] Write red graph tests for missing relation targets, self-relations, relation cycles, extends/conflicts without ADR evidence, hidden requirements, output overlap, shared-identity agreement, migration endpoint reachability, advertised package-major entry/exit paths, and catalog-role consistency.
- [ ] Enforce SPEC-BA02 revision 0.5 payload-owned `relation_evidence` and `legacy_states` declarations; reject missing/orphan evidence and unregistered/unused legacy-state endpoints without equating state IDs to signature IDs.
- [ ] Implement pure validators returning findings, never raising for ordinary contract defects.
- [ ] Add a synthetic unknown package and assert shared code contains no comparison against its package ID.
- [ ] Add request/discovery permutation tests over packages, payloads, contributions, providers, and migrations.
- [ ] Run focused tests; expect pass.
- [ ] Commit: `feat(v5): validate versioned package graphs`

### Task 11: Generated JSON Schemas and Drift Gate

**Files:**

- Create: `src/project_standards/package_contract/schemas.py`
- Create: `src/project_standards/schemas/standard-family.schema.json`
- Create: `src/project_standards/schemas/standard-payload.schema.json`
- Create: `src/project_standards/schemas/standards-catalog-source.schema.json`
- Create: `tests/package_contract/test_schemas.py`

- [ ] Write failing schema snapshot tests before creating the checked-in schemas.
- [ ] Generate Draft 2020-12 schemas from typed models, recursively set closed-object behavior, stable `$id` values, stable definition ordering, and a final newline.
- [ ] Validate every valid/invalid TOML fixture after converting it to a JSON-compatible object.
- [ ] Add a `generate_package_schemas(check: bool)` API that writes atomically or reports drift without mutation.
- [ ] Run twice and prove the second run produces no diff.
- [ ] Run `git diff --exit-code -- src/project_standards/schemas` after `--check`; expect no diff.
- [ ] Commit: `feat(v5): generate package contract schemas`

### Task 12: Authoring CLI Integration

**Files:**

- Create: `src/project_standards/package_contract/cli.py`
- Modify: `src/project_standards/standards_graph/cli.py`
- Modify: `src/project_standards/cli.py`
- Modify: `docs/usage.md`
- Create: `tests/package_contract/test_cli.py`
- Modify: `tests/test_standards_graph_cli.py`

- [ ] Write red tests for all public commands, human/JSON output, deterministic finding order, `--check`, root escape rejection, malformed args, and exit codes 0/1/2.
- [ ] Implement nested command dispatch while preserving every existing `project-standards standards validate-graph` and `render-catalog` contract.
- [ ] Keep filesystem writes limited to explicit schema/catalog/projection generation commands; validation is read-only.
- [ ] Add top-level help and installed-console-script tests.
- [ ] Run `uv run pytest tests/package_contract/test_cli.py tests/test_standards_graph_cli.py -q`; expect pass.
- [ ] Commit: `feat(v5): expose package authoring commands`

### Task 13: Canonical-to-Wheel Payload Projection

**Files:**

- Create: `src/project_standards/package_contract/projection.py`
- Create: `src/project_standards/payloads/` directories and file symlinks only when a V2 payload is added
- Modify: `pyproject.toml`
- Create: `tests/package_contract/test_projection.py`

- [ ] First add a temporary synthetic V2 payload under a test repository and prove `uv_build` dereferences a relative file symlink into wheel bytes. The test must skip neither Linux CI nor the sdist-to-wheel path.
- [ ] Write failing parity tests that reject regular files, absolute symlinks, broken links, links outside canonical payload roots, missing links, extra links, transformed bytes, and extra wheel members.
- [ ] Implement deterministic projection planning and `--check`. Apply mode creates parent directories and relative file symlinks only; it removes stale projection symlinks/empty directories but never touches canonical payload bytes.
- [ ] Add the required sdist inclusion configuration:

```toml
[tool.uv.build-backend]
source-include = ["standards/**", "catalogs/**"]
```

- [ ] Build both routes:

```bash
uv build --clear --sdist --wheel
uv build --wheel dist/project_standards-*.tar.gz --out-dir dist/from-sdist
```

- [ ] Install each wheel into isolated targets and compare every runtime file under `project_standards/payloads/{standard-id}/{version}/` byte-for-byte to its canonical source. Compare wheel member sets as well as digests.
- [ ] If `uv_build` changes symlink behavior or the sdist cannot preserve the projection, stop here and amend the architecture; do not fall back to checked-in copied payload files.
- [ ] Commit: `feat(v5): package canonical versioned payloads`

### Task 14: End-to-End Synthetic Contract and Scale Gate

**Files:**

- Create: `tests/package_contract/test_end_to_end.py`
- Create: `tests/package_contract/test_scale.py`
- Create: `tests/fixtures/package_contract/valid/full/`
- Create: `tests/fixtures/package_contract/valid/full/expected/catalog.toml`
- Complete the other synthetic valid repositories under `tests/fixtures/package_contract/valid/`.

- [ ] Create at least three data-only synthetic packages covering consumer, reference-only, and internal availability; all output declaration types; a shared contribution; provider declarations; referenced extension; automatic/manual migrations; and default/retained/candidate roles.
- [ ] Validate source, render consumer catalog, build/install wheel, rediscover installed payloads offline, and compare normalized repository facts.
- [ ] Deny network access during installed-payload discovery/validation.
- [ ] Generate 100 packages, 1,000 payloads, and 10,000 declared units in a temporary tree and assert validation/catalog generation completes under ten seconds on the normal Linux CI runner. Mark the test `performance` and run it in the repository CI gate, not on every focused loop.
- [ ] Run randomized discovery 100 times and assert identical findings, digests, schemas, and catalog bytes.
- [ ] Commit: `test(v5): prove package contract end to end`

### Task 15: Documentation, Traceability, and Foundation Closeout

**Files:**

- Modify: `docs/specs/2026-07-10-standard-bundle-authoring-v2-spec.md`
- Modify: `docs/handoff/specs-plans.md`
- Modify: `docs/STATUS.md`
- Modify: `docs/TODO.md`
- Modify: `CHANGELOG.md`
- Modify: `UPGRADING.md` only if author-facing commands require transitional guidance
- Create: `docs/reviews/2026-07-10-standard-bundle-authoring-v2-foundation-implementation-review.md`

- [ ] Update only the BA02 traceability rows actually proved by this plan. Use `Partial` for declaration-only provider/migration requirements until execution tests exist; do not mark FR-024–FR-031 complete early.
- [ ] Record the file-symlink projection invariant and the temporary V1/V2 preamble probe in `docs/handoff/conventions.md` if implementation confirms they are persistent patterns.
- [ ] Update plan status and commit evidence in handoff/tracker files.
- [ ] Run a whole-diff architecture review for package-ID branches, V1/V2 fact mixing, unsafe path reads, schema/model drift, copied projection files, and requirement overclaims.
- [ ] Resolve every Critical/Important review finding or explicitly return it to the owner before closeout.
- [ ] Commit: `docs(v5): close package contract foundation`

---

## Verification Gates

Run focused tests after every task. Before the final review commit, run from a clean index:

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
npm ci
uv run pytest tests/coherence
npx --no-install prettier --check .
npx --no-install markdownlint-cli2 "**/*.md"
uv run validate-frontmatter --config .project-standards.yml
uv run project-standards spec validate --config .project-standards.yml
uv run project-standards spec lint --config .project-standards.yml --strict
uv run project-standards standards validate-graph --root . --require-all-manifests
uv run project-standards standards validate-packages --root tests/fixtures/package_contract/valid/full --json
uv run project-standards standards generate-package-schemas --root . --check
uv run project-standards standards render-consumer-catalog --root tests/fixtures/package_contract/valid/full --catalog-major 5 --output expected/catalog.toml --check
uv run project-standards standards sync-payload-projection --root . --check
```

Expected results:

- Every command exits `0`.
- Coverage remains at least 85% branch coverage and does not regress package-contract modules below the repository norm.
- Schema, catalog, and projection checks report fresh output.
- The V1 graph stays green throughout this foundation phase.
- `git diff --check` reports no whitespace errors.
- A fresh `git status --short` contains only intentionally tracked plan-execution changes.

## Plan Completion Criteria

- BA02 family, payload, option, and catalog declarations have strict typed loaders and checked-in generated schemas.
- Complete payload inventory and canonical aggregate digest validation reject every undeclared or changed byte.
- Cross-package validation covers relationships, ownership scopes, shared identities, providers, extensions, migrations, and catalog roles without executing providers.
- Source and sdist-built wheels expose byte-identical payloads at the required version-qualified runtime path without copied authoring trees.
- Authoring CLI diagnostics are deterministic, safe, and machine-readable.
- V1 behavior remains unchanged, and no tracker claims live control-plane or current-package migration completion.
- The control-plane core plan can consume these models without redesigning the package contract.
