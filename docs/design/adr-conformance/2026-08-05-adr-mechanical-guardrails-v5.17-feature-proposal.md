---
schema_version: '1.1'
id: 'concept-f4q8mz-adr-mechanical-guardrails-and-conformance-foundation'
title: 'ADR Mechanical Guardrails and Conformance Foundation'
description: 'Formal v5.17.0 feature proposal for declarative provider inputs, generic read-only checks, and an opt-in ADR conformance package.'
doc_type: 'concept'
status: 'draft'
created: '2026-08-05'
updated: '2026-08-05'
tags:
  - 'adr'
  - 'conformance'
  - 'control-plane'
  - 'guardrails'
  - 'standards-platform'
aliases:
  - 'ADR mechanical guardrails'
  - 'ADR conformance foundation'
related:
  - 'docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md'
  - 'docs/TODO.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0025-mcp-service-and-sdk-boundary.md'
  - 'docs/adr/adr-0026-mcp-local-read-only-transport.md'
---

# ADR Mechanical Guardrails and Conformance Foundation

## Status and provenance

- **Status:** proposed feature and design starting brief
- **Target release:** Project Standards **5.17.0**
- **Proposed new package:** `adr-conformance@1.0`
- **Related ADR release:** `adr@1.5`, tracked by [issue #127](https://github.com/L3DigitalNet/project-standards/issues/127)
- **Related corpus remediation:** [issue #128](https://github.com/L3DigitalNet/project-standards/issues/128)
- **Feature tracking issue:** [issue #129](https://github.com/L3DigitalNet/project-standards/issues/129)
- **Operation:** create a new optional conformance package and the smallest generic platform capabilities it requires
- **Authority:** this document is a feature proposal, not an accepted ADR, implementation specification, or release commitment

This proposal supersedes the earlier assumption that the work could fit into 5.16.0. Project Standards 5.16.0 is published. The 5.17.0 train is now committed to additive ADR amendment vocabulary and remediation of the active ADR corpus. This proposal therefore narrows the first mechanical-guardrail release to a foundation that composes with that work instead of attempting the complete future ADR-governance system.

## Executive summary

ADR package 1.4 substantially improved authoring guidance. It defined governed concern, governed population, applicability condition, exclusions, reserved authority, equal-breadth rules, and a decision-boundary review. It intentionally did not infer semantic scope from prose. Its provider still checks only the three required MADR headings.

The repository's subsequent conformance assessment demonstrated the resulting gap: the guidance is useful, but it has no mechanical enforcement surface. The same assessment also exposed a related delivery defect: the repository remains on an older create-only ADR scaffold because the control plane has no supported mechanism for refreshing a consumer-owned scaffold after package adoption.

The next logical mechanical layer is not an LLM reviewer and not a policy language. It is a deterministic projection system:

1. ADR prose remains the authority for the decision and its human-readable boundary.
2. A consumer-owned TOML contract records the exact subset of that decision that can be checked mechanically.
3. An opt-in `adr-conformance` package validates the projection and evaluates a small closed set of rule kinds.
4. The control plane captures all provider inputs from payload declarations rather than adding another package-ID branch to `provider_inputs.py`.
5. A generic read-only repository check command runs applicable `validate`, `verify`, and `lint` providers for local use and CI.
6. CI is authoritative. MCP and agents receive the same findings through the existing dispatcher but do not become an independent source of truth.

The 5.17.0 minimum should support only static repository-state rules, mechanical scope containment, typed findings, and one dogfood target. Applicability resolution, plan binding, behavioral evidence, waivers, authorization, rule lifecycle, and dual-baseline policy transitions remain future work.

## 1. Current repository state

### 1.1 Released baseline

Project Standards 5.16.0 is the published baseline. Catalog 5 now carries the 5.16 successor packages, the full local and hosted verification fleets passed, and the remaining tracked issues are feature work rather than the prior defect backlog. See [Project Status](../../STATUS.md).

### 1.2 ADR 1.4 is guidance-first by design

The current ADR package is `adr@1.4`. Its standard says that decision-boundary quality is an authoring responsibility and that the release does not infer semantic scope from prose. The package provider checks only:

- whether a snapshot is a regular UTF-8 Markdown file with valid frontmatter;
- whether `doc_type` is `adr`; and
- whether the three required MADR level-2 headings exist when `require_sections = true`.

That boundary should remain intact. The ADR package should not become an open-ended semantic policy engine.

### 1.3 The 5.17 ADR train is already defined

Issue #127 introduces a first-class additive amendment relationship in `adr@1.5`. Issue #128 bundles that package advance with remediation of the active ADR corpus. The owner has already selected 5.17.0 as the release target and constrained `adr@1.5` to remain non-breaking so it can become the ordinary Catalog 5 default.

This proposal must not redesign or block that train. It should compose with it:

- `adr@1.5` owns ADR authoring, amendment, lifecycle, and document guidance.
- Corpus remediation owns correction of this repository's existing ADR records.
- `adr-conformance@1.0` owns optional mechanical projections and static verification.

### 1.4 The create-only scaffold gap is real but separate

Issue #128 shows that `docs/adr/adr.template.md` can remain on older bytes indefinitely because the ADR package correctly declares it `create-only`. The lock can record old consumer bytes under a newer selected package without giving the package overwrite authority.

The supported refresh mechanism must be decided generically by the control plane. Candidate forms include an explicit scaffold-refresh command, an `upgrade` provider, or another reviewed ownership transition. This proposal depends on that decision for repository dogfood but does not use conformance machinery to smuggle in overwrite authority.

### 1.5 Provider input selection is still engine-owned

[`src/project_standards/control_plane/provider_inputs.py`](../../../src/project_standards/control_plane/provider_inputs.py) explicitly states that provider input construction is not package-declarative today. The module contains the concentrated package-family branches because current `provider-input.schema.json` resources describe `snapshots` only as an unstructured object and do not say which repository paths a provider may read.

The module's documented retirement path is payload-declared input shapes. The open task in [Project Tasks](../../TODO.md) records the same direction. A new `adr-conformance` branch in that module would violate the intended architecture and make later retirement harder.

### 1.6 Generic read-provider execution exists, but not as a complete CLI surface

The payload contract already defines closed read-only operations with findings effects: `validate`, `verify`, `lint`, and `drift-check`. Reconciliation and MCP call the authoritative provider dispatcher. MCP's `validate_repo` and `drift_check` services already aggregate applicable providers without exposing arbitrary provider dispatch.

The local CLI has no equivalent generic repository-wide command. Top-level `validate` remains the Markdown Frontmatter validation surface. Mechanical ADR conformance therefore needs a generic local/CI entry point rather than another package-specific command.

## 2. Problem statement

Coding agents can read an ADR and still implement a rule too broadly, apply it to the wrong repository population, miss a load-bearing requirement, or treat an out-of-scope case as an exception. ADR 1.4 improves the authoring inputs to that decision but cannot stop a later implementation from drifting outside the accepted boundary.

A useful guardrail must answer deterministic questions such as:

- Does the repository still contain the exact dependency pin selected by an ADR?
- Are imports confined to the package boundary the ADR established?
- Does a rule target only paths inside the ADR's declared governed population?
- Does any mechanical rule intersect a path the ADR explicitly excluded?
- Is a mechanically enforced rule traceable to one active ADR and one stable rule ID?
- Can the same result be reproduced from source, installed wheel, local CLI, CI, and MCP?

The guardrail must not pretend to answer questions that remain semantic:

- Was the ADR's human boundary wise, complete, or appropriately narrow?
- Does prose imply a rule that the author never projected mechanically?
- Should an exception be granted?
- Did a human actually approve a policy change?

The feature must therefore separate human decision authority from deterministic enforcement while preserving one control plane and one provider model.

## 3. Goals

The initial release should:

1. Prevent mechanical rules from targeting paths outside their explicitly declared ADR boundary.
2. Enforce a small closed set of static repository-state rules without arbitrary code or shell commands.
3. Keep ADR prose authoritative and make every mechanical rule traceable to an ADR ID.
4. Add package-declared provider input capture without adding new standard-ID branches to shared control-plane code.
5. Expose a generic read-only repository check command suitable for CI and agent use.
6. Reuse the existing provider dispatcher, findings model, immutable payload model, referenced-extension mechanism, lock, and MCP services.
7. Keep adoption optional; enabling `adr` must not silently enable conformance.
8. Dogfood the design against at least one mature repository ADR with independent conventional tests.
9. Preserve all released package bytes and existing consumer behavior.
10. Establish explicit extension seams for later applicability, evidence, lifecycle, and authorization work.

## 4. Non-goals for 5.17.0

The initial release should not include:

- automatic extraction of rules or boundaries from ADR prose;
- LLM-authoritative pass/fail decisions;
- a general policy language such as Rego, CEL, or arbitrary expressions;
- arbitrary shell, executable, or consumer-named command rules;
- diff-aware applicability resolution beyond static path selection;
- plan or task binding;
- behavioral evidence contracts proving that particular tests ran;
- waiver approval or human-authorization providers;
- automatic exception generation;
- rule supersession, semantic compatibility, or full rule lifecycle;
- base-policy versus candidate-policy transition classification;
- agent-authorized policy changes;
- automatic ADR edits to make an implementation pass;
- cross-repository fleet orchestration;
- background services or watchers;
- compliance scores that obscure per-rule status;
- replacement of the existing handwritten tests used for dogfood;
- full retirement of every legacy branch in `provider_inputs.py`.

## 5. Architectural invariants

The following should be accepted before implementation.

### INV-001 — ADR prose remains authoritative

The ADR owns the decision, rationale, governed concern, population, applicability condition, exclusions, reserved authority, lifecycle, and amendment or supersession history.

### INV-002 — A conformance contract is a projection, not a second decision

The contract may encode only deterministic obligations already accepted by an ADR. It must not silently expand the ADR or become the sole human-readable authority.

### INV-003 — Every rule has a stable ADR-scoped identity

Rule IDs use a stable form such as `ADR-0025-R1`. Renumbering or reusing an ID for a materially different obligation is prohibited.

### INV-004 — Rule kinds are closed and declarative

The package defines an allowlisted rule registry. Consumer configuration supplies data only. It cannot name executable code, commands, Python symbols, plugins, or network resources.

### INV-005 — Mechanical scope cannot exceed declared decision scope

Every target, target set, or target pattern used by a rule must be contained by the decision's `governed_paths` and must not intersect its `excluded_paths`.

### INV-006 — Providers consume immutable snapshots only

The control plane resolves paths, validates containment, captures bytes and metadata, applies limits, and passes a deterministic snapshot to the provider. Providers never walk or write the live repository.

### INV-007 — Shared dispatch remains package-agnostic

No new `adr-conformance` literal may appear in the shared command boundary. A new package becomes executable through payload declarations, not control-plane switches.

### INV-008 — Static rules run in every authoritative check

Once the package is enabled and its contract is valid, every active static rule is evaluated in every ordinary conformance run. Agents cannot declare a rule irrelevant merely by omitting it from their plan.

### INV-009 — CI is authoritative

Local hooks, agent summaries, MCP, and editor feedback are advisory or early feedback. The protected repository gate determines whether a change conforms.

### INV-010 — Indeterminate blocking rules fail closed

Missing inputs, parse failures, unresolved paths, duplicate IDs, unsupported rule kinds, malformed contracts, or ambiguous scope relationships are findings, not silent skips.

### INV-011 — Existing packages remain independent

`adr-conformance` is opt-in and does not make `adr`, Markdown Frontmatter, or another package a hidden installation dependency. Its relationship to `adr` is explicit and mechanically validated.

### INV-012 — Released predecessors remain immutable and selectable

No prior ADR, control-plane, or bundle-authoring payload is edited. New behavior ships through successors and additive tool changes.

## 6. Selected design

### 6.1 Separate `adr-conformance` from the ADR authoring package

Create a new consumer family rather than expanding `adr@1.5` into an enforcement engine.

Recommended relationship:

```toml
[payload]
standard = "adr-conformance"
version = "1.0"
availability = "consumer"

[capabilities]
provides = ["adr.conformance"]
consumes_platform = ["project-standards.reconcile"]

[relations]
companions = []
extends = ["adr"]
conflicts = []
```

The `extends` edge requires immutable decision evidence under the Standard Bundle Authoring contract. The new project ADR should state that ADR authoring and ADR conformance are separate authorities, that conformance is optional, and that enabling the extension does not alter the MADR document contract.

Initialization continues to enable no package. A consumer that wants ADRs without mechanical enforcement can continue to enable only `adr`.

### 6.2 Authority split

| Surface | Authority |
| --- | --- |
| Decision, rationale, boundary, exclusions, amendment, supersession | ADR prose and frontmatter |
| Deterministic obligation projection | Consumer-owned conformance contract |
| Rule grammar and checker semantics | Immutable `adr-conformance` payload |
| Path capture, containment, snapshots, limits, dispatch | Unified control plane |
| Pass/fail in a protected repository | CI and repository branch policy |
| Early feedback | Local CLI and MCP |

### 6.3 Consumer-owned contract

Use one repository-owned TOML file for the initial release:

```text
.standards/extensions/adr-conformance/contracts.toml
```

The path should be selected through one closed package option and declared as a referenced extension. The central lock records the path and digest without claiming, rewriting, or deleting the file.

Recommended package options:

```toml
[standards.adr-conformance]
enabled = true
version = "1.0"

[standards.adr-conformance.config]
contract_path = ".standards/extensions/adr-conformance/contracts.toml"
```

The initial release should support one file only. Directories, overlays, imports, and generated fragments are deferred until a real consumer requires them.

### 6.4 Contract shape

Recommended starting contract:

```toml
schema_version = "1.0"

[capture]
include = [
  "pyproject.toml",
  "src/project_standards/mcp_server/**/*.py",
  "src/project_standards/mcp_services/**/*.py",
]
exclude = []

[[decisions]]
adr_id = "adr-0025-project-standards-mcp-service-and-sdk-boundary"
document = "docs/adr/adr-0025-project-standards-mcp-service-and-sdk-boundary.md"
governed_paths = [
  "pyproject.toml",
  "src/project_standards/mcp_server/**",
  "src/project_standards/mcp_services/**",
]
excluded_paths = [
  "src/project_standards/control_plane/**",
  "standards/**",
]

[[decisions.rules]]
id = "ADR-0025-R1"
kind = "toml-array-member"
target = "pyproject.toml"
pointer = "/project/dependencies"
value = "mcp==2.0.0"

[[decisions.rules]]
id = "ADR-0025-R2"
kind = "python-import-boundary"
targets = ["src/project_standards/**/*.py"]
module = "mcp"
allowed_importers = ["src/project_standards/mcp_server/**"]

[[decisions.rules]]
id = "ADR-0025-R3"
kind = "python-import-boundary"
targets = ["src/project_standards/mcp_services/**/*.py"]
forbidden_modules = [
  "mcp",
  "project_standards.mcp_server",
]
```

The explicit `capture` section is intentional in v1. The control plane must know which files to snapshot before provider execution, while rule interpretation belongs to the provider. The provider must verify that capture is no broader than the union of the declared decision boundaries and that every rule target is included in the captured corpus.

A later input-capture contract may derive paths directly from typed rule fields. The initial release should prefer one simple, auditable fixed-pointer shape over a general wildcard JSON-pointer language.

### 6.5 Declarative provider input capture

Add a generic input-capture declaration to a successor of the Standard Bundle Authoring package and its payload model.

Candidate manifest form:

```toml
[[input_captures]]
id = "conformance-repository"
kind = "referenced-extension-globs"
extension = "contracts"
include_pointer = "/capture/include"
exclude_pointer = "/capture/exclude"
include_extension_content = true
max_files = 5000
max_total_bytes = 52428800

[[providers]]
id = "verify-conformance"
operation = "verify"
kind = "python"
phase = "verify"
effect = "findings"
entrypoint = "payload:provider-code#run_verify"
input_schema = "provider-input"
output_schema = "provider-findings"
input_capture = "conformance-repository"
resources = []
```

The exact field names require specification, but the contract must provide:

- one closed capture-kind registry;
- one declared referenced extension;
- fixed pointers to include and exclude string arrays;
- repository-relative path and glob validation;
- deterministic expansion and sorting;
- root containment and symlink safety;
- regular-file and encoding metadata;
- file-count, per-file, and aggregate-byte limits;
- explicit inclusion of the extension bytes and digest;
- stable findings when capture cannot be completed.

Compatibility behavior:

- New packages may use `input_capture`.
- Existing released payloads without it continue through the concentrated compatibility logic in `provider_inputs.py`.
- New package-ID branches are prohibited.
- Existing families can move to declarative capture through ordinary immutable successor releases.
- Full deletion of `provider_inputs.py` is a later milestone after every supported family is migrated.

### 6.6 Generic repository check command

Expose the existing generic read-provider model to local CLI and CI.

Recommended working surface:

```text
project-standards check [--repo <dir>] [--standard <id>] [--operation <operation>] [--json]
```

Default behavior should run every applicable enabled provider whose operation is one of:

- `validate`
- `verify`
- `lint`

`drift-check` remains explicit because it answers a different operational question. The exact command spelling may change during specification, but the semantics should not:

- resolve enabled packages and effective configuration through the control plane;
- build inputs only through the package declaration or legacy compatibility seam;
- invoke the same provider dispatcher used by reconciliation and MCP;
- aggregate typed findings deterministically by package, provider, path, and identity;
- return stable human and versioned JSON output;
- never mutate the repository;
- support narrowing by standard for debugging without changing the authoritative all-package CI invocation;
- return distinct exit categories for clean, findings, and invocation or authority errors.

This is an aggregate operation, not arbitrary provider dispatch. It remains consistent with the MCP decision to expose `validate_repo` rather than a user-selected provider execution tool.

### 6.7 Initial rule registry

Keep the first release deliberately small.

#### `toml-value`

Assert that one JSON-pointer-addressed TOML scalar equals an exact value.

#### `toml-array-member`

Assert that one JSON-pointer-addressed TOML array contains one exact scalar member. Ordering should be configurable only if an ADR explicitly governs order; default semantics are membership only.

#### `python-import-boundary`

Parse Python with the standard library AST and assert exact module-prefix rules over deterministic target files. It should support:

- one module or module prefix;
- allowed importer path patterns;
- forbidden importer path patterns or forbidden module prefixes;
- `import x`, `import x.y`, `from x import y`, and relative-import normalization where resolvable;
- syntax errors as blocking findings;
- no dynamic import inference in v1.

No checker may invoke a compiler, shell, package manager, network command, or consumer executable.

### 6.8 Scope-containment validation

Before evaluating a rule, the provider must prove all of the following:

1. The referenced ADR document exists as a captured regular file.
2. Its frontmatter `id` equals `adr_id` and `doc_type` equals `adr`.
3. The ADR is active under the selected ADR contract.
4. The decision contract has at least one governed path.
5. Every rule target is included by at least one governed path.
6. No rule target intersects any excluded path.
7. Every rule target is present in the captured corpus.
8. The capture corpus is no broader than the union of all decision-governed paths required for evaluation.
9. Rule IDs are unique globally and correctly scoped to their ADR.
10. Unsupported or malformed rules block evaluation rather than disappearing.

The provider does not infer these paths from ADR prose. Human review confirms that the projection accurately reflects the accepted ADR. Mechanical containment ensures the projection cannot then govern more than it explicitly declares.

### 6.9 Findings contract

The initial package can use the existing findings shape:

- `code`
- `severity`
- `path`
- `identity`
- `message`
- `hint`

Recommended identities and codes:

| Condition                   | Code              | Identity                       |
| --------------------------- | ----------------- | ------------------------------ |
| malformed contract          | `ADR-CONTRACT`    | contract field or JSON pointer |
| missing or mismatched ADR   | `ADR-DECISION`    | ADR ID                         |
| rule outside governed scope | `ADR-SCOPE`       | rule ID                        |
| rule intersects exclusion   | `ADR-EXCLUSION`   | rule ID                        |
| unsupported rule kind       | `ADR-RULE-KIND`   | rule ID                        |
| missing or invalid target   | `ADR-TARGET`      | rule ID                        |
| rule violation              | `ADR-CONFORMANCE` | rule ID                        |

Human output should name the ADR, rule, target, observed fact, expected fact, and remediation without reproducing sensitive file content. JSON output should remain stable and deterministic.

### 6.10 CI and MCP integration

The authoritative consumer gate runs the generic check command with no standard narrowing. The `adr-conformance` package may supply a managed or semantically composed workflow that invokes that command, following the existing workflow ownership and `runner-labels` conventions. The exact workflow mode belongs in the implementation specification.

MCP requires no package-specific tool. Once the provider input is package-declarative, the existing `validate_repo` service should include the new provider through the same resolver and dispatcher. Contract tests must prove CLI and MCP return equivalent findings for the same installed distribution and repository snapshot.

### 6.11 Known v1 policy-change limitation

The initial system protects ordinary implementation changes against an already accepted contract. It does not yet prove that a change modifying an ADR, its conformance contract, and the applied lock in the same branch is semantically non-weakening.

For 5.17.0:

- ADR documents, `contracts.toml`, package code, and control-plane code remain human-reviewed policy surfaces.
- CI must still validate their structure and evaluate the resulting candidate contract.
- The PR description and review must call out policy-surface changes explicitly.
- Existing independent conventional tests remain required for dogfood.

A later release should add base-policy versus candidate-policy evaluation, semantic rule digests, transition classification, and authorization-backed policy changes. This limitation must be documented rather than hidden.

## 7. Interaction with issues #127 and #128

### 7.1 Required sequencing

Recommended 5.17.0 order:

1. Design and land #127 as additive `adr@1.5`.
2. Decide the generic create-only scaffold refresh mechanism needed by #128 item 1.
3. Remediate the active ADR corpus using the sanctioned 1.5 amendment form.
4. Accept the project ADR authorizing the separate `adr-conformance` package and generic input-capture capability.
5. Implement the generic provider-input declaration and aggregate check command.
6. Implement `adr-conformance@1.0`.
7. Dogfood against the remediated ADR 0025 and add the authoritative gate.
8. Qualify and publish the combined 5.17.0 release.

Design work for steps 4–6 may proceed while corpus prose is being prepared, but final dogfood should use the remediated corpus and selected 1.5 document form.

### 7.2 What belongs to `adr@1.5`

- amendment relationships and lifecycle;
- amendment body form;
- decision-boundary review for amendments;
- authoring templates and guidance;
- any additive frontmatter-schema support required by #127;
- migration or upgrade guidance for ad hoc amendment banners.

### 7.3 What belongs to the generic control plane

- create-only scaffold refresh or upgrade mechanism;
- package-declared provider input capture;
- repository path containment and snapshot construction;
- generic aggregate read-provider execution;
- lock and referenced-extension handling.

### 7.4 What belongs to `adr-conformance@1.0`

- conformance-contract schema;
- scope-containment rules;
- static rule registry and checkers;
- contract and rule findings;
- conformance-specific documentation, examples, and agent summary;
- optional CI integration.

## 8. Dogfood target

Use ADR 0025 as the first dogfood decision because it already freezes deterministic obligations with independent conventional tests:

- exact dependency pin `mcp==2.0.0`;
- only `mcp_server` may import `mcp`;
- `mcp_services` may import neither `mcp` nor `mcp_server`;
- SDK types must not leak into the service facade.

The first three obligations fit the initial checker registry. Public-signature SDK-type leakage requires a richer Python API checker and should remain covered by the existing handwritten tests until a future rule kind is justified.

Dogfood must use controlled negative fixtures:

1. Remove or alter the dependency pin; the conventional test and `ADR-0025-R1` both fail.
2. Import `mcp` from `mcp_services`; the conventional test and `ADR-0025-R2` or `R3` both fail.
3. Import `mcp` from an allowed adapter path; both remain green.
4. Broaden a rule target into an excluded path; contract validation fails before rule evaluation.
5. Remove the ADR document or change its ID; contract validation fails.
6. Corrupt a target file; parsing fails closed.

The handwritten tests must not be deleted in 5.17.0. They are independent evidence that the new engine is not validating only its own assumptions.

## 9. Implementation workstreams

### Workstream A — Architecture and specifications

- Accept a project ADR for the authority split, separate package, and generic platform seam.
- Specify the input-capture manifest contract.
- Specify aggregate CLI semantics and exit codes.
- Specify the conformance contract and checker semantics.
- Resolve workflow integration and package options.

### Workstream B — Standard Bundle Authoring successor

- Add `input_captures` and provider `input_capture` declarations.
- Extend schemas, models, validators, templates, catalog rendering, and installed projections.
- Reject undeclared captures, duplicate IDs, invalid pointers, unsafe paths, unsupported kinds, and inconsistent provider references.
- Preserve all released authoring payloads.

### Workstream C — Control-plane capture and dispatch

- Resolve referenced extension bytes through the lock.
- Parse and validate capture include/exclude arrays.
- Expand paths deterministically under the explicit repository root.
- Enforce symlink, path, file-type, count, and size boundaries.
- Build immutable snapshots and typed input.
- Use declarative capture before legacy compatibility dispatch.
- Prohibit new package-family branches.

### Workstream D — Generic repository check

- Add the aggregate command and service API.
- Reuse selected-package resolution and provider dispatch.
- Produce stable human and JSON output.
- Prove direct CLI and MCP parity.
- Add CI integration without arbitrary provider selection.

### Workstream E — `adr-conformance@1.0`

- Add family index, payload, closed config schema, referenced extension, schemas, provider, documentation, examples, and tests.
- Implement contract validation and the three initial rule kinds.
- Add typed findings and deterministic ordering.
- Add adoption and troubleshooting guidance.

### Workstream F — Dogfood and release

- Author the project conformance contract for ADR 0025.
- Run negative controls and conventional-test parity.
- Add the authoritative repository gate.
- Prove source, wheel, installed, catalog, lock, MCP, and consumer behavior.
- Publish only after #127, #128, and the generic scaffold-refresh decision are reconciled.

## 10. Acceptance criteria

### Package and graph

- `adr-conformance@1.0` is a complete immutable consumer payload.
- Its relationship to `adr` is explicit and backed by decision evidence.
- It is not enabled merely because `adr` is enabled.
- Catalog 5 advertises exactly one default for the new family without removing any prior package version.
- All package, graph, schema, projection, and source-distribution checks pass.

### Provider input authority

- The new provider receives every repository byte through one declared `input_capture`.
- No new package ID appears in shared control-plane dispatch files or the legacy compatibility table.
- Path expansion is deterministic and bounded.
- Unsafe symlinks, traversal, non-regular files, over-limit captures, missing extensions, and stale lock digests fail closed.
- Existing packages without declarations retain byte-equivalent behavior through the compatibility seam.

### Contract validation

- The contract is schema-validated before target capture or rule evaluation.
- ADR ID, document path, status, and `doc_type` are verified.
- Duplicate decision or rule IDs fail.
- Every rule target is contained by governed paths.
- No rule target intersects excluded paths.
- Capture cannot silently exceed the union of required governed paths.
- Unknown fields and rule kinds fail under a closed schema.

### Rule evaluation

- `toml-value`, `toml-array-member`, and `python-import-boundary` have exact documented semantics.
- Parsing failures are findings, not skips.
- Results are deterministic across filesystem enumeration order.
- Findings contain stable codes and rule identities.
- Clean, violation, and invocation-error exit classes are distinct.

### Integration

- The generic CLI aggregate and MCP `validate_repo` produce equivalent findings.
- Check mode is provably non-mutating.
- CI runs the all-package authoritative command.
- The selected dogfood rules fail all controlled negative fixtures and pass the repository baseline.
- Existing ADR 1.5 heading validation and frontmatter validation remain independent and green.
- Existing conventional ADR 0025 tests remain in place and agree with the new rules.

### Release

- 5.17.0 classification remains MINOR.
- `adr@1.5`, `adr-conformance@1.0`, and any internal Standard Bundle Authoring successor are advertised without altering released predecessors.
- Source wheel, sdist-derived wheel, and installed distribution contain byte-identical payloads.
- The repository's selected package state and lock converge with an empty second reconcile.
- Documentation clearly states the v1 policy-change limitation and future transition path.

## 11. Test strategy

The implementation specification should require at least:

- payload model round trips for every capture kind and failure mode;
- manifest schema rejection of duplicate, dangling, or incompatible capture references;
- referenced-extension containment and digest tests;
- glob normalization, ordering, case, symlink, traversal, and root-boundary tests;
- file-count, per-file, and aggregate-byte limit tests;
- stale lock and concurrent file-change tests;
- source-tree versus installed-wheel provider parity;
- direct dispatcher versus aggregate CLI versus MCP result parity;
- contract parser tests for unknown keys, duplicate IDs, malformed TOML, missing ADRs, ID mismatch, and superseded decisions;
- scope-containment matrix tests including overlapping include/exclude patterns;
- TOML pointer, scalar type, array membership, missing-key, and malformed-document tests;
- Python AST tests for import forms, module prefixes, relative imports, syntax errors, allowed paths, and forbidden paths;
- deterministic human and JSON finding order;
- non-mutation tests for every failure path;
- complete dogfood negative controls;
- regression tests proving no prior payload bytes changed;
- a real consumer fixture with `adr` only and another with `adr` plus `adr-conformance`.

## 12. Rollout and adoption

A consumer adoption flow should be explicit:

```bash
project-standards standards enable adr-conformance --version 1.0
# Author and review .standards/extensions/adr-conformance/contracts.toml
project-standards reconcile
project-standards reconcile --apply
project-standards check
```

Expected rollout properties:

- Existing consumers see no change until they enable the package.
- Enabling the package with no valid contract fails with actionable guidance rather than silently doing nothing.
- Disabling the package removes only its managed integration and lock records; the consumer-owned contract remains untouched.
- A contract change is review-visible and changes the referenced-input digest.
- Rules are evaluated from the exact installed package implementation, not consumer-selected code.

## 13. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| The contract becomes a second, broader decision authority | Require ADR linkage, scope containment, and explicit projection language. |
| The engine gains another package-specific branch | Require payload-declared capture before the package can ship. |
| Capturing whole repositories becomes expensive or invasive | Contract-driven include/exclude sets, deterministic expansion, and hard limits. |
| Rules become an arbitrary policy language | Closed rule registry, no expressions, shell, plugins, or external commands. |
| Agents weaken the contract in the same PR | Document the v1 limitation, keep policy surfaces human-reviewed, retain independent tests, add dual-baseline protection later. |
| `adr@1.5` becomes coupled to enforcement | Separate package, separate options, explicit relationship, opt-in adoption. |
| 5.17 becomes overloaded | Hold the release to three checker kinds, one contract file, one capture kind, one dogfood ADR, and no lifecycle or authorization features. |
| Create-only scaffold work gets conflated with conformance | Track and decide scaffold refresh as a separate generic control-plane feature. |
| MCP becomes a second authority | Reuse the same dispatcher and snapshots; CI remains authoritative. |

## 14. Deferred roadmap

### Next layer

- base-policy and candidate-policy evaluation;
- semantic rule digests;
- policy-transition classification and self-weakening detection;
- rule lifecycle: draft, active, deprecated, superseded, retired;
- reciprocal rule relationships and graph validation;
- formal coverage accounting from ADR obligations to rule dispositions.

### Later layer

- authoritative applicability and impact resolver;
- plan and task binding to policy baseline digests;
- behavioral evidence adapters for tests, schemas, APIs, performance, and generated artifacts;
- authorization-backed waivers and non-waivable rules;
- change-triggered requirements;
- cross-language fact adapters;
- incremental content-addressed verification;
- durable normalized result manifests;
- governance analytics;
- diff-specific agent context and optional fast-feedback hooks.

## 15. Decisions required before specification

1. Approve a separate `adr-conformance` consumer package rather than expanding `adr`.
2. Approve `extends = ["adr"]` as the relationship and require a project ADR as evidence.
3. Approve one consumer-owned TOML contract at `.standards/extensions/adr-conformance/contracts.toml` for v1.
4. Approve the explicit top-level capture include/exclude arrays as the initial generic input-capture source.
5. Approve the three initial rule kinds.
6. Approve ADR 0025 as the dogfood target and retention of independent conventional tests.
7. Approve a generic aggregate read-only CLI command; settle its final spelling in the specification.
8. Decide whether the package ships a managed CI workflow or only a command and composition contribution.
9. Confirm the v1 same-change policy-weakening limitation is acceptable for 5.17.0.
10. Keep create-only scaffold refresh as a separate control-plane decision coordinated with #128.
11. Confirm that full `provider_inputs.py` retirement is deferred; 5.17 adds the generic successor path and forbids new branches.
12. Confirm the combined 5.17 release boundary remains manageable alongside #127 and #128.

## 16. Recommended tracking decomposition

After approval, split implementation into bounded tracked items:

1. **Architecture decision:** authority split, separate package, CI authority, and v1 limitations.
2. **Provider input specification:** payload capture schema and compatibility behavior.
3. **Control-plane implementation:** generic capture resolution and snapshot construction.
4. **Generic check command:** CLI/service/MCP parity and exit contracts.
5. **ADR Conformance package:** contract schema, provider, checker registry, docs, and adoption.
6. **Dogfood:** ADR 0025 contract, negative controls, and repository gate.
7. **Release qualification:** combined 5.17 source, wheel, installed, catalog, lock, and hosted proof.

Each item should preserve the explicit exclusions in this proposal and append new work rather than widening an in-flight task silently.

## Sources

- [ADR Standard 1.4](../../../standards/adr/versions/1.4/README.md)
- [ADR 1.4 conformance assessment](../../reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md)
- [Issue #127 — amendment vocabulary](https://github.com/L3DigitalNet/project-standards/issues/127)
- [Issue #128 — active corpus remediation](https://github.com/L3DigitalNet/project-standards/issues/128)
- [Issue #129 — ADR mechanical guardrail foundation](https://github.com/L3DigitalNet/project-standards/issues/129)
- [Project Tasks](../../TODO.md)
- [Unified Consumer Standards Control Plane](../../adr/adr-0023-unified-consumer-standards-control-plane.md)
- [Stable Generic Agent and Tooling Interface](../../adr/adr-0005-stable-generic-agent-tooling-interface.md)
- [Standard Provider and Plugin Model](../../adr/adr-0006-standard-provider-plugin-model.md)
- [Standard Graph Validation Gate](../../adr/adr-0007-standard-graph-validation-gate.md)
- [Independent Standard Packages and Relationship Taxonomy](../../adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md)
- [MCP Service and SDK Boundary](../../adr/adr-0025-mcp-service-and-sdk-boundary.md)
- [MCP Local Read-Only Transport](../../adr/adr-0026-mcp-local-read-only-transport.md)
- [Standard Bundle Authoring 2.6](../../../standards/standard-bundle-authoring/versions/2.6/README.md)
- [`provider_inputs.py`](../../../src/project_standards/control_plane/provider_inputs.py)
- [Provider payload contract](../../../src/project_standards/package_contract/payload.py)
- [CLI usage reference](../../usage.md)
