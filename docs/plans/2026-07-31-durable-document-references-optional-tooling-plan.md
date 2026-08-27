---
plan_format: 3
title: 'Durable Document References Optional Tooling Implementation Plan'
slug: 'durable-document-references-optional-tooling'
status: active
revision: 1
revises_revision: 0
revision_reason: 'restore the unexecuted legacy master at plan format 3 so the current engine can validate, generate, and govern it'
pause_reason: ''
source: 'SPEC-GSF3'
spec_ref: 'docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md'
created: 2026-07-31
updated: 2026-08-27
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
---

# Durable Document References Optional Tooling Implementation Plan

> **Definition, not state.** Authoring drafts live in `.project-pipeline/2026-07-31-durable-document-references-optional-tooling/authoring/`; generated execution status and evidence pointers live in `.project-pipeline/2026-07-31-durable-document-references-optional-tooling/execution/`. Executors reach the engine through their own installed `plan-authoring` skill; this repository ships no plan binary.

## 1. Objective

Ship the optional `project-standards references` command group in the main `project-standards` wheel so that specification and ADR identifiers become reliably navigable and objectively drift-checkable at repository scope. The subsystem derives a unique canonical identifier-to-document registry from authored declarations, enforces first-prose and navigation linking, reports broken and wrong-target local links, validates schema-specific relationship metadata, renders a disposable JSON/DOT document graph, and previews mechanically certain link repairs behind an explicit apply. No standards package owns it, no standard selection enables it, no MCP surface is added, and no persistent cache, registry, or graph is created. The principal invariant is that authored Markdown remains the only authority: `check`, reconciliation preview, and stdout `graph` leave the repository byte-identical, and every derived artifact is regenerable from current bytes.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md` | normative | SPEC-GSF3: scope, non-goals, deferrals, constraints, FR/NFR/IR/DR requirements, design decisions, edge cases, error taxonomy, testing gates, and the MS-0–MS-5 milestone shape this plan decomposes. | revision 0.2, 2026-08-27 (`status: draft`) | §§1, 3–13; T1–T14 |
| `request` | normative | Owner decision of 2026-08-27 under issue #178: restore this master at plan format 3 at the same path, preserving the original 14-task intent and scope; do not implement it in the same change. | 2026-08-27 | §§1, 3, 8–9, 13 |
| `issue:L3DigitalNet/project-standards#178` | normative | Records that the legacy master's `plan.py sync` header targets deleted code and that the format-3 successor engine is the only remaining governance path. Restricts scope to unblocking the plan, not implementing it. | verified 2026-08-27 | §§2–3, 13 |
| `repo:docs/handoff/specs-plans.md` | decision | Records SPEC-GSF3 as a draft specification with an active, wholly unimplemented 14-task plan; no task has ever been executed, so restoration starts from revision 1 with no checkpoint history to reconstruct. | 2026-08-27 | §§3–4, 8; T1 |
| `repo:src/project_standards/cli.py` | current-state evidence | Top-level lazy command dispatch and the `validate` aggregate that already composes frontmatter, ID, and metadata-reference validation; the seam a `references` group and an opt-in aggregate contribution must extend. | verified 2026-08-27 | §§4–5; T6, T10, T11 |
| `repo:src/project_standards/control_plane/models.py::DesiredConfig` | current-state evidence | The consumer desired-state model still admits only `project_standards` and `standards`; `ControlHeader.schema_version` is `Literal["1.0", "1.1"]` and its `role` validator is the repository's precedent for gating a new consumer-owned key behind a header version. | verified 2026-08-27 | §§4–5, 11; T1 |
| `repo:src/project_standards/schemas/consumer-config.schema.json` | current-state evidence | The generated consumer-config schema is closed at the top level (`additionalProperties: false` over `project_standards` and `standards`), so a sibling `[tools]` table is a schema-shape change, not an unvalidated addition. | verified 2026-08-27 | §§4–5, 11; T1 |
| `repo:src/project_standards/control_plane/codec.py` | current-state evidence | Canonical TOML decode/encode path that must preserve a consumer-owned `[tools.references]` table across read/render cycles. | verified 2026-08-27 | §5; T1 |
| `repo:src/project_standards/control_plane/config_edit.py` | current-state evidence | Standards-only config mutation path that must not drop an unrelated tool namespace. | verified 2026-08-27 | §5; T1 |
| `repo:src/project_standards/control_plane/migration.py` | current-state evidence | Config migration and rendering path, including the existing `1.0` → `1.1` header transition that OQ-001 must be answered against. | verified 2026-08-27 | §§5, 11; T1 |
| `repo:src/project_standards/control_plane/schemas.py` | current-state evidence | Generated-schema projection that must emit the new reference envelopes and the updated consumer-config schema. | verified 2026-08-27 | §5; T1 |
| `repo:src/project_standards/validate_references.py` | current-state evidence | The existing opt-in cross-file frontmatter pass: id uniqueness, referential integrity, supersede reciprocity, date ordering, ADR sequence; warnings never fail, and an unmatched well-formed ADR id is assumed external. Its standalone semantics must survive unchanged. | verified 2026-08-27 | §§4–5, 10; T5, T10 |
| `repo:src/project_standards/validate_frontmatter.py::parse_frontmatter` | current-state evidence | The single frontmatter parsing authority the new scanner must reuse instead of adding a second grammar. | verified 2026-08-27 | §5; T2 |
| `repo:src/project_standards/validate_id.py::_ADR_ID_RE` | current-state evidence | The single owner of the canonical `adr-NNNN-...` identifier grammar; the ADR namespace adapter consumes it rather than restating it. | verified 2026-08-27 | §5; T3 |
| `repo:src/project_standards/_filesystem.py` | current-state evidence | Contained descriptor-relative staging and atomic per-file replacement; the only sanctioned publication primitive for guarded graph output and reconciliation apply. | verified 2026-08-27 | §5; T7, T9 |
| `repo:src/project_standards/control_plane/executor.py` | current-state evidence | The existing guarded mutation boundary whose per-file atomicity — and absence of any multi-file transaction — bounds what FR-019 may claim. | verified 2026-08-27 | §§5, 10; T9 |
| `repo:.standards/config.toml` | current-state evidence | This repository's own producer-role config at header `schema_version = "1.1"`; the dogfood target that T12 extends with an honest `[tools.references]` scope. | verified 2026-08-27 | §§4–5, 10; T1, T12 |
| `repo:.standards/lock.toml` | current-state evidence | Resolved package versions for this repository (project-spec 1.9, adr 1.6, markdown-frontmatter 1.13) that the namespace adapters compose. | release 5.23.0 | §4; T3 |
| `repo:docs/specs/README.md` | current-state evidence | The maintained specification index; the concrete configured navigation surface whose completeness FR-006 enforces during dogfood. | verified 2026-08-27 | §§5, 9; T12 |
| `repo:docs/adr/adr-0025-mcp-service-and-sdk-boundary.md` | current-state evidence | A representative member of the 32-document ADR corpus supplying real canonical declarations, human aliases, and cross-references for the ADR adapter and the dogfood baseline. | verified 2026-08-27 | §§4, 9; T3, T12 |
| `repo:standards/markdown-frontmatter/versions/1.13/field-values.md` | normative | The Markdown Frontmatter relationship and source policy whose `related`, `depends_on`, `supersedes`, and `superseded_by` path forms FR-010 must validate in their own terms rather than normalizing into Project Specification identifiers. | Markdown Frontmatter 1.13 (resolved) | §5; T5 |
| `repo:pyproject.toml` | current-state evidence | Runtime floor, dependency set, and packaging configuration; establishes that Pydantic, PyYAML, and pytest are available and that Hypothesis is not. | verified 2026-08-27 | §§3, 5; T1, T11 |
| `repo:tests/test_installed_wrappers.py` | current-state evidence | The existing installed-wheel probe harness the distribution proof extends. | verified 2026-08-27 | §7; T11 |
| `repo:tests/package_compatibility/matrix.py` | current-state evidence | The candidate/installed compatibility matrix that must keep passing and gains reference-command coverage. | verified 2026-08-27 | §7; T11 |
| `repo:tests/control_plane/test_models.py` | current-state evidence | Existing desired-config parse, render, codec, and generated-schema coverage that pins current behavior before T1 extends it. | verified 2026-08-27 | §7; T1, T10 |
| `repo:scripts/verify.sh` | operational evidence | The canonical repository gate (fast and `--full` lanes) and the authority for lane names and TMPDIR/coverage placement. | verified 2026-08-27 | §§7, 12; T12, T14 |
| `repo:meta/versioning.md` | normative | Repository versioning policy that classifies the public feature and configuration-contract change before release. | verified 2026-08-27 | §§10, 12; T14 |
| `repo:README.md` | current-state evidence | Documents the candidate-wheel runtime recipe every distribution and dogfood proof depends on. | verified 2026-08-27 | §§7, 12; T11, T12, T14 |
| `repo:AGENTS.md` | normative | Markdown Tooling gate: Prettier owns formatting and markdownlint owns structure over the Git-tracked scope; binds every document task. | verified 2026-08-27 | §§7, 12; T12, T14 |
| `repo:CLAUDE.md` | normative | Heavy-workload routing (`rexec -- COMMAND`), the candidate-wheel dogfood non-negotiable, and the handoff validator wrappers. | verified 2026-08-27 | §3.4; T1–T14 |

Conflict precedence: SPEC-GSF3 revision 0.2 governs every behavioral, interface, and severity question; where it is silent, the owner `request` and issue #178 govern process and scope. Repository implementation and tests are current-state evidence establishing seams and preserved behavior only — they never widen or narrow a spec requirement. Where the legacy 2026-07-31 master and SPEC-GSF3 disagree, the specification wins; the legacy master is retained here only as the source of the approved 14-task decomposition, and its two duplicated decision IDs (`D-004`, `D-005` each appearing twice) are corrected in §5.4 rather than carried forward.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- A first-party `project_standards.references` package and a top-level `references {check,graph,reconcile}` command group in the main wheel.
- A closed optional `[tools.references]` desired-config namespace, its codec/migration/edit preservation, and its generated schema projection.
- Contained corpus discovery with distinct identity and policy scopes plus one shared exclusion set, and one structural Markdown scanner for this subsystem.
- Project Specification and ADR namespace adapters over a document-derived canonical registry with explicit external-identifier mappings.
- First-prose, navigation, configured-index completeness, local-link, wrong-target, relationship, and advisory policy with stable codes and the group-wide exit taxonomy.
- Versioned finding, graph, and reconciliation-plan envelopes with deterministic human, JSON, and DOT renderings.
- Preview-first reconciliation with group precondition preflight and atomic per-file application through the existing guarded writer.
- Opt-in aggregate composition into `project-standards validate` with separately attributed legacy and new findings.
- Source-tree, candidate-wheel, installed-wheel, real-corpus, security, and cold-run benchmark evidence.
- This repository's own dogfood configuration, objective blocking-drift remediation, user documentation, and release classification.

### 3.2 Out of Scope and Deferred

- Permanent non-goals (SPEC-GSF3 NG-001–NG-007): making this a standards package or an adoption dependency; replacing any existing validator; deriving `related:` from body mentions; committing a generated graph; running a database, daemon, watcher, or UI; checking external URL health over the network; rewriting prose or inferring ambiguous intent.
- Deferred with revisit triggers (SPEC-GSF3 WH-001–WH-005): additional identifier namespaces; persistent or incremental scan caching; MCP resources or tools; relocation into `project-toolbox`; cross-file transactional rollback.
- Adding Hypothesis or any other runtime or dev dependency; parametrized pytest carries the v1 invariants.
- Answering OQ-001 on this plan's own authority. Whether the consumer-config header advances to `schema_version = "1.2"` is an owner decision recorded in SPEC-GSF3 §21; T1 implements the answer, it does not choose it.
- Publishing a release, tagging, or pushing. `meta/versioning.md` classification is in scope; publication is separately authorized.
- Implementing any task in the same change that restores this master.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| Plan owns | The `project_standards.references` subsystem, its public CLI/config/report/graph/plan contracts, its tests and fixtures, the opt-in aggregate dispatch, this repository's dogfood scope and remediated corpus, and the user documentation for all of it. |
| Depends on | SPEC-GSF3 as the behavioral authority; the owner's OQ-001 decision before T1's configuration contract freezes; the existing frontmatter parser, ADR identifier grammar, guarded writer, control-plane config authority, and candidate-wheel runtime recipe. |
| Does not own | The Project Specification, ADR, or Markdown Frontmatter schemas and validators; the standards package graph; standards adoption or package selection; MCP; external URL availability; editorial `related:` decisions; release publication; `project-toolbox` relocation. |
| Must preserve | Standalone `validate-references` codes, severities, and exit behavior; every existing package validator and standards-graph result; parse, render, and `config_digest` behavior for configs that omit `[tools]`; the guarded writer's public contract; candidate-wheel and installed-wheel parity; the authored meaning of every document T12 edits. |

### 3.4 Constraints and Authorization

- **EG-001 — configuration gate:** T1 may not freeze the `[tools.references]` contract until SPEC-GSF3 OQ-001 carries an owner decision. Until then T1 is blocked, not guessed; record the decision in the specification's revision log before implementing it.
- Python 3.14 floor with the existing dependency set only (Pydantic, PyYAML, pytest, Ruff, BasedPyright). No new runtime or dev dependency.
- Reuse the single existing authority for each shared concern: `validate_frontmatter.parse_frontmatter` for frontmatter, `validate_id._ADR_ID_RE` for the ADR identifier grammar, control-plane models/codec/schemas for configuration, and `_filesystem` for contained atomic publication. A second parser, grammar, or config authority is a defect.
- Read paths make no network call and mutate no authored byte. Explicit graph publication may touch only its named guarded target outside both the identity and policy scopes.
- Human, JSON, DOT, finding-code, schema, and exit-status contracts are frozen by tests before integration; version-one envelopes are unstamped.
- Heavy workloads route through `rexec -- COMMAND`: `scripts/verify.sh` (any lane), `make go-check`, and full pytest runs. Targeted single-file pytest may run locally with the extracted candidate wheel first on `PYTHONPATH`. Wheel and sdist builds, signing, tagging, and publication stay local.
- Dogfood validation runs against the extracted candidate-wheel runtime per `README.md`, not the bare virtualenv.
- Every touched Markdown file passes the `AGENTS.md` Prettier and markdownlint gate over the Git-tracked scope.
- No task commits, pushes, publishes, or mutates GitHub work state outside its own separately authorized workflow. Execution state is mutated only through the executor's own `plan-authoring state` command.

## 4. Current State and Target State

### 4.1 Current State

The repository validates document contracts independently and at document scope. `validate-frontmatter`, `validate-id`, and the opt-in `validate-references` pass enforce Markdown Frontmatter schema, identifier form, and a narrow cross-file metadata corpus; `validate-references` treats unresolved references as warnings and assumes a well-formed unmatched ADR identifier is external. `project-standards spec validate` and `spec lint` own Project Specification structure over an explicit `include_patterns` allowlist. The standards graph models standard-package contracts, not document navigation. `docs/specs/README.md` is authored navigation with no mechanical completeness obligation.

Nothing composes those contracts at repository scope. No tool proves that a formal identifier maps to exactly one canonical document, that an identifier-bearing link resolves to the document declaring that identity, that required first-prose and navigation references are linked, or that supported relationship metadata resolves.

`DesiredConfig` admits only `project_standards` and `standards`, and the generated `consumer-config.schema.json` closes the top level with `additionalProperties: false`. `ControlHeader.schema_version` is `Literal["1.0", "1.1"]`, and its `role` field is rejected under `1.0` — the repository's own precedent that a new consumer-owned key arrives with a header version. This repository's config sits at `schema_version = "1.1"` with `role = "producer"`.

`_filesystem` already provides contained descriptor-relative staging and atomic per-file replacement; the control-plane executor uses it and offers no multi-file transaction. The candidate-wheel runtime recipe in `README.md` is the dogfood path, and `scripts/verify.sh` is the canonical gate.

No task of this plan has ever been executed. The prior master was authored on 2026-07-31 in a retired format whose bridge (`scripts/plan.py`) was deleted, so the current engine refuses `validate`, `sync`, and `pause` on it; issue #178 records that the plan is therefore ungoverned rather than merely stale. There are no `Plan-*` checkpoints to recover.

### 4.2 Target State

An installed `project-standards` wheel always exposes `references check`, `references graph`, and `references reconcile`, independently of any selected standards package and of MCP. A repository may run them explicitly with configuration or equivalent CLI scope arguments; aggregate validation includes reference findings only when `[tools.references].enabled = true`.

Discovery resolves two scopes — adapter-recognized canonical locations for identity, and configured authored, index, and historical paths for policy — with one shared exclusion set. One scanner parses each selected file at most once into a typed record. Namespace adapters build identity candidates; the canonical registry rejects duplicate identities and alias collisions before any policy, graph, or reconciliation output exists. Policy emits deterministically ordered typed findings; blocking classes are objective and advisory classes are editorial. `graph` renders only validated local nodes and typed edges as byte-deterministic JSON or DOT. `reconcile` previews by default and mutates only under `--apply`, which recomputes its own plan, preflights every containment and digest precondition as a group, and replaces each target atomically without claiming multi-file rollback.

This repository dogfoods the tool: an honest declared scope, a recorded full-corpus baseline, objective blocking drift remediated, `docs/specs/README.md` complete for its declared namespaces and roots, and the aggregate gate enabled only after its declared scope is clean. The feature is documented, classified under `meta/versioning.md`, and proven identical from source tree, candidate wheel, and installed wheel, with a reproducible cold-run benchmark on record. Publication remains the only separately authorized step.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Document reference policy | Per-document schema validation only; no repository-level identity or navigation authority. | One optional composition layer proving unique canonical identity, required linking, and resolved relationships. | Every existing validator's own schema authority, codes, severities, and exit behavior. |
| CLI surface | No `references` group. | `references {check,graph,reconcile}` in the main wheel, available without any selected standard or MCP. | Existing top-level dispatch, help output for other commands, and lazy-import cost. |
| Aggregate validation | Frontmatter, ID, metadata-reference, and control-plane validation. | Optionally one more attributed contributor, gated solely on `[tools.references].enabled`. | Disabled-by-default behavior; no standard selection may enable it; legacy findings keep their own codes and severities. |
| Consumer configuration | Closed top level: `project_standards`, `standards`. | Additional closed optional `[tools.references]` namespace, governed by the OQ-001 header decision. | Configs omitting `[tools]` keep byte-identical rendering and an unchanged `config_digest`. |
| Derived artifacts | None for documents. | Unstamped versioned finding, graph, and reconciliation-plan envelopes; no persisted state. | Authored Markdown as the only authority; read paths leave the repository byte-identical. |
| Mutation | Control-plane reconcile only. | Preview-first document reconciliation over a bounded safe allowlist through the existing guarded writer. | Containment, symlink refusal, digest preconditions, atomic per-file replacement, and no transaction claim. |
| This repository's corpus | Authored navigation with unmeasured drift. | Declared dogfood scope with a recorded baseline and zero blocking findings. | Authored meaning of every edited document; no waiver, suppression, or scope narrowing to hide drift. |
| Plan governance | Legacy master the current engine refuses. | Format-3 master the engine validates, generates, and governs. | The approved 14-task decomposition, scope, and non-goals. |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Reference models and envelopes | absent | Typed parsed records plus closed versioned finding, graph, and plan envelopes with stable ordering | `src/project_standards/references/models.py`, `schemas.py` | T1 |
| Tool configuration | Closed two-key desired config | Closed optional `[tools.references]` composed into desired state, preserved through codec, edit, and migration | `repo:src/project_standards/control_plane/models.py::DesiredConfig`, `codec.py`, `config_edit.py`, `migration.py`, `schemas.py`, `src/project_standards/schemas/consumer-config.schema.json` | T1 |
| Corpus discovery | absent | Contained resolution of adapter identity locations, configured policy scopes, and one shared exclusion set | `src/project_standards/references/discovery.py` | T2 |
| Markdown scanner | Frontmatter parsing only | One single-pass structural scan exposing ranges, links, mentions, and metadata with physical coordinates | `src/project_standards/references/markdown.py`, reusing `repo:src/project_standards/validate_frontmatter.py::parse_frontmatter` | T2 |
| Namespace adapters and registry | absent | Spec and ADR declaration/alias interpretation over an adapter-neutral identity model; unique local registry with separate external mappings | `src/project_standards/references/identities.py`, reusing `repo:src/project_standards/validate_id.py::_ADR_ID_RE` | T3 |
| Policy checker | absent | First-prose, navigation, index completeness, local-link, wrong-target, relationship, and advisory rules with stable codes | `src/project_standards/references/policy.py`, `relationships.py` | T4, T5 |
| Command surface and reporting | Top-level dispatch without a references group | `references {check,graph,reconcile}` with human/JSON parity and the group-wide exit taxonomy | `src/project_standards/references/cli.py`, `reporting.py`, `repo:src/project_standards/cli.py` | T6, T7, T8, T11 |
| Graph builder | absent | Deterministic validated-only node/edge projection with JSON and DOT renderers and guarded optional publication | `src/project_standards/references/graph.py` | T7 |
| Reconciliation planner and applier | absent | Allowlisted span edits with digest preconditions; group preflight and atomic per-file publication | `src/project_standards/references/reconcile.py`, `application.py`, using `repo:src/project_standards/_filesystem.py` | T8, T9 |
| Aggregate composition | Frontmatter/ID/metadata/control-plane contributors | One additional opt-in attributed contributor | `repo:src/project_standards/cli.py` | T10 |
| Dogfood adoption | No tool scope declared | Honest declared scope, recorded baseline, remediated corpus, complete specification index | `repo:.standards/config.toml`, `repo:docs/specs/README.md`, `docs/**/*.md` | T12 |
| Documentation and release readiness | No reference-tooling documentation | User guide, landing-page summary, package reference, benchmark record, versioning classification | `docs/reference-tooling.md`, `repo:README.md`, `src/project_standards/README.md`, `repo:meta/versioning.md` | T14 |

### 5.2 Control / Data / State Flow

Configuration or equivalent CLI scope arguments resolve two scopes. Enabled namespace adapters declare where identity may be declared; that set is independent of policy `include`. Configured `include`, `indexes`, and `historical` select the policy corpus. `exclude` subtracts from both, so a generated copy or fixture can neither be enforced nor create an identity.

The scanner reads each selected file at most once and emits one typed record carrying frontmatter, structural ranges, explicit links, visible formal-identifier mentions, and supported relationship values with one-based physical coordinates. Adapters convert declarations into identity candidates. The canonical registry is the trust boundary: it fails closed on duplicate canonical identifiers or alias collisions, and external mappings are held separately so they can never shadow a local identity or become a graph node.

Only after the registry validates do the three consumers run. The policy checker produces findings and never mutates. The graph builder consumes validated identities and resolved relationships only; an unresolved reference stays a finding rather than becoming an invented node. The reconciliation planner converts an allowlisted subset of findings into preconditioned span edits over visible label text only.

Mutation crosses exactly one trust boundary. `reconcile --apply` rescans, recomputes its plan in that invocation, verifies containment and every content digest as a group, and only then delegates per-file atomic replacement to `_filesystem`. There is no persisted plan and no cross-invocation apply token; a previously printed preview is informative output, never an authorization artifact.

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | New optional read-only checking, graph rendering, and bounded repair; no existing validator's standalone behavior changes. | PV-T4-001, PV-T5-001, PV-T6-001, PV-T10-001 | T4, T5, T6, T10 |
| Architecture / dependency direction | yes | The subsystem depends on control-plane config, frontmatter parsing, ADR grammar, and the guarded writer; none of them may depend on it, and no MCP or standards-selection import may enter the references path. | PV-T11-001 | T3, T11 |
| Public / cross-task interface | yes | Three subcommands, one exit taxonomy, and three versioned envelopes are frozen by contract tests before integration. | PV-T1-001, PV-T6-001, PV-T7-001, PV-T8-001 | T1, T6, T7, T8 |
| Data / state | yes | Derived records are in-memory only; the subsystem persists no cache, registry, graph, or plan. | PV-T1-001, PV-T13-001 | T1, T13 |
| Configuration | yes | One closed optional namespace; configs omitting it keep byte-identical rendering and an unchanged `config_digest`; header versioning follows the OQ-001 decision. | PV-T1-001 | T1 |
| Security / trust | yes | Containment, symlink and non-regular refusal, no network access, group digest preflight before the first write, and bounded diagnostics that echo no unrelated source content. | PV-T9-001, PV-T13-001 | T9, T13 |
| Compatibility / migration | yes | Legacy validator codes, severities, and exits are unchanged; overlapping findings are attributed rather than merged; older configs remain valid. | PV-T10-001, PV-T11-001 | T10, T11 |
| Operations / deployment | yes | The command ships in the main wheel and behaves identically from source, candidate, and installed distributions; the aggregate gate is enabled only after the declared scope is clean. | PV-T11-001, PV-T12-001, PV-T14-001 | T11, T12, T14 |
| Documentation | yes | A user guide, landing-page summary, and package reference distinguish explicit availability, aggregate opt-in, standards adoption, and MCP. | PV-T14-001 | T14 |
| Durable evidence | yes | The cold-run benchmark record and the dogfood full-corpus baseline are durable records, not reproducible-on-demand output. | PV-T12-001, PV-T14-001 | T12, T14 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Extend the existing desired-config authority for `[tools.references]` rather than parsing TOML independently. | A second config parser would fork canonical rendering and digest behavior; the closed generated schema is the only place that can reject unknown keys once. Rejected: a standalone `references.toml`, which would double the configuration surface and break `config_digest` coherence. | `repo:src/project_standards/control_plane/models.py::DesiredConfig`; SPEC-GSF3 IR-005 | T1, T10 |
| D-002 | Use one subsystem scanner plus the existing frontmatter authority; policy, graph, and reconciliation consume typed records only. | Competing regular expressions across three consumers would drift silently and produce span edits the scanner never sanctioned. Rejected: per-consumer ad-hoc matching, which is faster to write and impossible to keep consistent. | SPEC-GSF3 §8.5; `repo:src/project_standards/validate_frontmatter.py::parse_frontmatter` | T2–T5, T8 |
| D-003 | Keep external identifier mappings entirely outside the local graph: they resolve policy but create no node or edge. | The graph is a local document relationship view; inventing remote nodes from configuration would make it a partial and misleading authority. Rejected: synthesising external nodes for completeness. | SPEC-GSF3 FR-009, FR-011, DR-004 | T3, T7 |
| D-004 | Discover identities at adapter-owned canonical locations independently of policy `include`, with `exclude` subtracting from both scopes. | Phased adoption must resolve legitimate targets outside the enforced subset without letting an excluded copy claim an identity. Rejected: tying identity to `include`, which makes every partial adoption report false unknown-identifier failures. | SPEC-GSF3 FR-003, EC-014 | T2, T3, T12 |
| D-005 | Count formal identifiers only in visible prose and link labels; never rewrite a link destination, autolink target, raw URL, or path-like token. | ADR filenames and repository URLs embed identifier-shaped substrings; treating them as prose produces both false positives and unsafe rewrites. Rejected: span-agnostic textual replacement. | SPEC-GSF3 FR-007, FR-016, EC-015 | T2, T4, T8 |
| D-006 | Give configured indexes completeness responsibility; an ordinary `References` section enforces linking of what it lists, nothing more. | Completeness needs a declared namespace and root boundary to be testable; imposing it on every `References` heading would make the rule unfalsifiable. Rejected: repository-wide completeness inference. | SPEC-GSF3 FR-006, EC-017 | T4, T12 |
| D-007 | Recompute the reconciliation plan inside the apply invocation; never accept a prior preview as an apply token. | A stored plan is hidden state whose freshness cannot be proven across invocations; recomputation makes the digest preflight meaningful. Rejected: plan files consumed by a later `--apply`, which is the more familiar UX and the less honest guarantee. | SPEC-GSF3 FR-015, IR-004, EC-011 | T8, T9 |
| D-008 | Use existing pytest with parametrized invariants; add no property-testing dependency. | Dependency expansion was not approved and parametrized tables already cover the v1 invariant set. Rejected: Hypothesis, which would give better shrinking at the cost of an unapproved dev dependency. | `repo:pyproject.toml`; SPEC-GSF3 §17.2 | T2, T7, T8, T9, T13 |
| D-009 | Restore this master at plan format 3 at its original path and identity (`created` 2026-07-31, slug unchanged) rather than retiring it or creating a new document. | The 14-task decomposition, requirement mapping, and scope remain correct and unexecuted; only the governance format is dead. A new path would orphan the `docs/handoff/specs-plans.md` pointer and the `Plan-Id` derived from `created` and `slug`. Rejected: retirement (loses approved design work) and a new dated document (breaks the recorded pointer for no benefit). | `request`; `issue:L3DigitalNet/project-standards#178`; `repo:docs/handoff/specs-plans.md` | T1–T14 |

## 6. Requirements and Acceptance

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Expose the reference subsystem from the main wheel without requiring any standards-package selection. | SPEC-GSF3 §7.1 | Must | T11 | T11 | PV-T11-001 |
| FR-002 | Run aggregate reference validation only when `[tools.references].enabled` is true, while explicit commands run from configuration or equivalent CLI scope. | SPEC-GSF3 §7.1 | Must | T10 | T10 | PV-T10-001 |
| FR-003 | Separate adapter identity discovery from configured policy scope, with `exclude` subtracting from both. | SPEC-GSF3 §7.1 | Must | T2 | T2 | PV-T2-001 |
| FR-004 | Build one canonical registry through spec and ADR declaration adapters with bounded identifier and alias grammar. | SPEC-GSF3 §7.1 | Must | T3 | T3 | PV-T3-001 |
| FR-005 | Require the first prose reference to another local document's formal identifier to link to its canonical document. | SPEC-GSF3 §7.1 | Must | T4 | T4 | PV-T4-001 |
| FR-006 | Require every formal identifier listed under a `References` heading to link, and require each configured index to cover its declared namespaces and roots completely. | SPEC-GSF3 §7.1 | Must | T4 | T4 | PV-T4-001 |
| FR-007 | Exempt frontmatter, code, self-identity, destinations, autolinks, raw URLs, path-like tokens, historical content, and post-first-link occurrences from first-reference enforcement. | SPEC-GSF3 §7.1 | Must | T4 | T2, T4 | PV-T2-001, PV-T4-001 |
| FR-008 | Report every broken local Markdown link as blocking and verify that an identifier-bearing label resolves to the document declaring that identifier. | SPEC-GSF3 §7.1 | Must | T4 | T4 | PV-T4-001 |
| FR-009 | Treat enabled namespaces as local by default; resolve external identifiers only through explicit stable links or configured `external_ids`. | SPEC-GSF3 §7.1 | Must | T3 | T3 | PV-T3-001 |
| FR-010 | Validate supported relationship metadata in its governing schema's own reference form without cross-schema normalization. | SPEC-GSF3 §7.1 | Must | T5 | T5 | PV-T5-001 |
| FR-011 | Fail unresolved or noncanonical relationship values as blocking at the exact source field; only a local `prior_specs` resolution creates a `prior-spec` edge. | SPEC-GSF3 §7.1 | Must | T5 | T5 | PV-T5-001 |
| FR-012 | Emit only advisories for strong-evidence `related:` suggestions, one-sided nonrequired relationships, orphan current documents, and redundant targets. | SPEC-GSF3 §7.1 | Must | T5 | T5 | PV-T5-001 |
| FR-013 | Report all independent findings `check` can safely determine without modifying source or derived artifacts. | SPEC-GSF3 §7.1 | Must | T6 | T6 | PV-T6-001 |
| FR-014 | Emit deterministic JSON or DOT containing validated local nodes and typed edges. | SPEC-GSF3 §7.1 | Must | T7 | T7 | PV-T7-001 |
| FR-015 | Make `reconcile` a read-only typed preview by default and mutate only under `--apply`, which recomputes the current plan and consumes no prior preview. | SPEC-GSF3 §7.1 | Must | T9 | T9 | PV-T9-001 |
| FR-016 | Propose only uniquely mapped visible first-reference, wrong-target, and configured-index label corrections; never rewrite a destination, autolink, URL, or path-like token. | SPEC-GSF3 §7.1 | Must | T8 | T8 | PV-T8-001 |
| FR-017 | Never add, remove, or infer `related:` entries or other editorial relationship metadata during reconciliation. | SPEC-GSF3 §7.1 | Must | T8 | T8 | PV-T8-001 |
| FR-018 | Verify repository containment and every content-hash precondition as a group before replacing any file. | SPEC-GSF3 §7.1 | Must | T9 | T9 | PV-T9-001 |
| FR-019 | Replace each changed file atomically and claim no cross-file transactional rollback. | SPEC-GSF3 §7.1 | Must | T9 | T9 | PV-T9-001 |
| FR-020 | Preserve existing standards-package validator behavior, keep the package graph distinct from the document graph, and attribute overlapping findings instead of silently changing an existing result. | SPEC-GSF3 §7.1 | Must | T10 | T10 | PV-T10-001 |
| NFR-001 | Use stable ordering and serialization so unstamped findings, graphs, and plans are byte-identical across runs over identical bytes. | SPEC-GSF3 §7.2 | Must | T13 | T13 | PV-T13-001 |
| NFR-002 | Perform no network call and modify no authored source on any read path; explicit graph output may touch only its guarded target. | SPEC-GSF3 §7.2 | Must | T13 | T13 | PV-T13-001 |
| NFR-003 | Expose the same semantic findings, locations, severities, and limits through versioned human and JSON envelopes. | SPEC-GSF3 §7.2 | Must | T6 | T6 | PV-T6-001 |
| NFR-004 | Behave equivalently from the source tree, candidate wheel, and installed wheel. | SPEC-GSF3 §7.2 | Must | T11 | T11 | PV-T11-001 |
| NFR-005 | Record a reproducible cold-run benchmark over this repository without hardcoded corpus counts. | SPEC-GSF3 §7.2 | Must | T14 | T14 | PV-T14-001 |
| NFR-006 | Isolate namespace-specific declaration and alias rules behind adapters while policy consumes an adapter-neutral typed model. | SPEC-GSF3 §7.2 | Must | T3 | T3 | PV-T3-001 |
| NFR-007 | Use stable codes and one-based physical source locations without echoing unrelated document content. | SPEC-GSF3 §7.2 | Must | T13 | T13 | PV-T13-001 |
| IR-001 | Expose `project-standards references {check,graph,reconcile}` and exactly those v1 subcommands. | SPEC-GSF3 §7.3 | Must | T11 | T11 | PV-T11-001 |
| IR-002 | Apply one group-wide exit contract: `0` for success including advisory-only, `1` for policy/identity/publication/precondition/apply/internal failure, `2` for invocation or configuration error. | SPEC-GSF3 §7.3 | Must | T13 | T13 | PV-T13-001 |
| IR-003 | Emit graph JSON by default and DOT on request, to stdout unless an explicit guarded path outside both reference scopes is supplied. | SPEC-GSF3 §7.3 | Must | T7 | T7 | PV-T7-001 |
| IR-004 | Emit a versioned typed plan by default; `--apply` rescans, recomputes, emits, and preflights its own plan and accepts no prior plan as input. | SPEC-GSF3 §7.3 | Must | T9 | T9 | PV-T9-001 |
| IR-005 | Accept an optional closed `[tools.references]` namespace in `.standards/config.toml`, reject unknown keys, preserve configs lacking it byte-identically, and fail an empty effective scope as error `2`. | SPEC-GSF3 §7.3 | Must | T1 | T1 | PV-T1-001 |
| IR-006 | Include reference findings in `project-standards validate` only when `[tools.references].enabled = true`. | SPEC-GSF3 §7.3 | Must | T10 | T10 | PV-T10-001 |
| DR-001 | Retain path, declared identity, title, kind, lifecycle status, structural ranges, links, mentions, and relationship values in the parsed document record. | SPEC-GSF3 §7.4 | Must | T2 | T2 | PV-T2-001 |
| DR-002 | Map each local canonical identifier to exactly one parsed document with unambiguous accepted aliases; duplicates and collisions block. | SPEC-GSF3 §7.4 | Must | T3 | T3 | PV-T3-001 |
| DR-003 | Carry schema version, stable code, severity, path, physical location, message, and guidance in each finding, in a closed deterministic envelope. | SPEC-GSF3 §7.4 | Must | T1 | T1 | PV-T1-001 |
| DR-004 | Give each local node a deterministic identity and each valid local relationship a typed directed edge; unresolved and externally mapped identities are neither. | SPEC-GSF3 §7.4 | Must | T7 | T7 | PV-T7-001 |
| DR-005 | Carry a source digest per planned file and a bounded nonoverlapping span and replacement per edit, with mandatory preconditions. | SPEC-GSF3 §7.4 | Must | T8 | T8 | PV-T8-001 |
| DR-006 | Persist no cache, graph, registry, or reconciliation state by default; a complete read-only run leaves the repository and user configuration unchanged. | SPEC-GSF3 §7.4 | Must | T13 | T13 | PV-T13-001 |
| REQ-001 | Adopt the tool in this repository honestly: record the full-corpus blocking baseline, remediate objective blocking drift, index SPEC-GSF3, and enable the aggregate gate only once the declared scope has no blocking findings. Introduce no waiver or suppression mechanism and never narrow scope to hide known drift. | SPEC-GSF3 §18.2, MS-2, MS-5 | Must | T12 | T12 | PV-T12-001 |
| REQ-002 | Deliver the §18.7 documentation set and classify the public feature and configuration-contract change under `meta/versioning.md` before release qualification. | SPEC-GSF3 §18.3, §18.7 | Must | T14 | T14 | PV-T14-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** targeted `PYTHONPATH=$PWD/build/wheel-runtime uv run pytest PATH` for single-file work; `rexec -- uv run pytest` and `rexec -- ./scripts/verify.sh [--full]` for suite and gate lanes; `uv run ruff check .`; `uv run ruff format --check .`; `rexec -- uv run basedpyright`; `uv run pip-audit`; the `AGENTS.md` Prettier and markdownlint invocations over the Git-tracked scope; `PYTHONPATH=$PWD/build/wheel-runtime uv run project-standards validate` for the dogfood gate.
- **Oracles:** SPEC-GSF3's requirement, edge-case, and ERR tables; the frozen JSON Schemas for the three envelopes; `validate_id._ADR_ID_RE` and the Project Specification `spec_id` pattern as the identifier grammars; the existing `_filesystem` writer contract; pre-change repository content hashes; the standalone `validate-references` output captured before T10 as the compatibility baseline; this repository's real ADR and specification corpus.
- **Negative controls:** a scanner that treats a link destination or `adr-0025-...` filename as prose; a registry that lets an `external_ids` entry shadow a local identity; a policy pass that enforces completeness on an ordinary `References` heading; a planner that rewrites a URL span; an apply path that writes the first file before checking the last digest; an aggregate contributor that runs with `enabled = false` or that reclassifies a legacy warning as an error; a graph that emits a placeholder node for an unresolved reference; a diagnostic that echoes surrounding prose.
- **Test layers:** unit (scanner, adapters, registry, policy, planner), characterization (existing config parse/render, legacy validator output, guarded writer semantics), contract (envelope schemas, exit matrix, human/JSON parity, DOT determinism), integration (CLI, configuration, aggregate composition, filesystem effects), security (containment, symlink and non-regular refusal, network denial, stale-write refusal, bounded diagnostics), real-corpus (this repository), distribution (source, candidate wheel, installed wheel), performance (cold run), documentation (examples exercised against candidate bytes).
- **External environments:** none. Every proof runs locally or on the rexec worker; no network access is required and read paths must prove network denial.
- **Evidence:** repeatable local output is ephemeral. Two records are durable because they cannot be reproduced later from committed source alone: the T12 full-corpus baseline and the T14 cold-run benchmark. Both are defined in Appendix C.
- **Late failure:** a failure discovered during T13 or T14 blocks that verification task, appends a correction task with `corrects:` and `discovered_from:`, and reruns from the corrected anchor. It never silently reopens or rewrites a completed task.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Freeze models, schemas, and tool configuration | active | brownfield-behavior | P1 | None | IR-005, DR-003 | PV-T1-001 | no / control-plane config files |
| T2 | Discover and structurally scan identity and policy scopes | active | behavior | P1 | T1 | FR-003, FR-007, DR-001 | PV-T2-001 | no / T1 models |
| T3 | Build specification and ADR adapters and the canonical registry | active | behavior | P1 | T1, T2 | FR-004, FR-009, NFR-006, DR-002 | PV-T3-001 | no / T2 records |
| T4 | Enforce body, navigation, and local-link policy | active | behavior | P2 | T2, T3 | FR-005, FR-006, FR-007, FR-008 | PV-T4-001 | no / `policy.py` shared with T5 |
| T5 | Enforce relationship and advisory policy | active | behavior | P2 | T3, T4 | FR-010, FR-011, FR-012 | PV-T5-001 | no / `policy.py` shared with T4 |
| T6 | Deliver check reporting and exit contracts | active | behavior | P2 | T4, T5 | FR-013, NFR-003 | PV-T6-001 | no / `references/cli.py` shared with T7, T8, T9 |
| T7 | Generate deterministic local JSON and DOT graphs | active | behavior | P3 | T3, T4, T5 | FR-014, IR-003, DR-004 | PV-T7-001 | no / `references/cli.py` shared with T6, T8, T9 |
| T8 | Plan only allowlisted reconciliation edits | active | behavior | P3 | T4, T5, T6 | FR-016, FR-017, DR-005 | PV-T8-001 | no / `references/cli.py` shared with T6, T7, T9 |
| T9 | Apply plans through guarded per-file replacement | active | behavior | P3 | T8 | FR-015, FR-018, FR-019, IR-004 | PV-T9-001 | no / `references/cli.py` shared with T6, T7, T8 |
| T10 | Compose opt-in aggregate validation | active | brownfield-behavior | P4 | T1, T6 | FR-002, FR-020, IR-006 | PV-T10-001 | no / `repo:src/project_standards/cli.py` shared with T11 |
| T11 | Prove top-level and wheel distribution parity | active | brownfield-behavior | P4 | T6, T7, T9, T10 | FR-001, NFR-004, IR-001 | PV-T11-001 | no / `repo:src/project_standards/cli.py` shared with T10 |
| T12 | Reconcile and enable the dogfood corpus | active | transition | P4 | T10, T11 | REQ-001 | PV-T12-001 | no / repository-wide document edits |
| T13 | Harden security, determinism, and failure boundaries | active | behavior | P5 | T7, T9, T10 | NFR-001, NFR-002, NFR-007, IR-002, DR-006 | PV-T13-001 | no / none |
| T14 | Record performance, document, and qualify release | active | documentation | P5 | T11, T12, T13 | NFR-005, REQ-002 | PV-T14-001 | no / none |

## 9. Implementation Tasks

### Phase P1: Contracts, Discovery, and Identity

#### T1: Freeze models, schemas, and tool configuration

- **disposition:** active
- **outcome:** A closed optional `[tools.references]` configuration parses, resolves, and renders through the existing desired-config authority, and the three public envelopes serialize deterministically, while a config that omits `[tools]` is byte- and digest-identical to today.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [IR-005, DR-003]
- **proof:** [PV-T1-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#73-interface-requirements, repo:src/project_standards/control_plane/models.py::DesiredConfig, repo:src/project_standards/schemas/consumer-config.schema.json, repo:src/project_standards/control_plane/codec.py::parse_config, repo:src/project_standards/control_plane/config_edit.py::load_control_state, repo:src/project_standards/control_plane/migration.py::plan_legacy_migration, repo:src/project_standards/control_plane/schemas.py::generate_control_plane_schemas, repo:tests/control_plane/test_models.py::test_desired_config_is_strict_frozen_and_deterministically_ordered]
- **consumes:** [the owner's EG-001 decision on SPEC-GSF3 OQ-001, the existing closed desired-config model and generated schema, existing canonical TOML codec behavior]
- **produces:** [references-config-v1, references-finding-envelope-v1, references-graph-envelope-v1, references-plan-envelope-v1]
- **preserves:** [parse, resolution, rendering, and `config_digest` behavior for every config without `[tools]`; all existing generated schema bytes for unrelated documents; standards-only edit and migration semantics]
- **invariants:** [unknown keys are rejected without echoing their values; an explicit or enabled run with an empty effective scope is error `2`; envelope serialization order is a function of semantic content, never of input order]
- **executor_discretion:** [private model and helper names, internal module split inside `references/`, fixture organization]
- **files:** [`src/project_standards/references/models.py` (create; owner T1), `src/project_standards/references/config.py` (create; owner T1), `src/project_standards/references/schemas.py` (create; owner T1), `src/project_standards/control_plane/models.py` (modify; owner T1), `src/project_standards/control_plane/codec.py` (modify; owner T1), `src/project_standards/control_plane/config_edit.py` (modify; owner T1), `src/project_standards/control_plane/migration.py` (modify; owner T1), `src/project_standards/control_plane/schemas.py` (modify; owner T1), `src/project_standards/schemas/consumer-config.schema.json` (modify via generation; owner T1), `src/project_standards/schemas/reference-findings.schema.json` (create via generation; owner T1), `src/project_standards/schemas/reference-graph.schema.json` (create via generation; owner T1), `src/project_standards/schemas/reference-plan.schema.json` (create via generation; owner T1), `tests/references/test_models.py` (test; owner T1), `tests/references/test_config.py` (test; owner T1), `tests/references/test_schemas.py` (test; owner T1), `tests/control_plane/test_models.py` (modify; owner T1), `tests/control_plane/test_schemas.py` (modify; owner T1)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T1 checkpoint; the control-plane files return to their characterized bytes. Never recover by loosening the generated schema's `additionalProperties`, by removing the empty-scope error, or by proceeding past EG-001 with a guessed header decision.
- **acceptance:** PV-T1-001 proves the documented `[tools.references]` keys round-trip canonically, unknown keys and an empty effective scope are rejected with bounded diagnostics, the three envelopes reject extra fields and serialize byte-identically under permuted semantically-equal input, and a config without `[tools]` produces byte-identical rendering and an unchanged `config_digest`.
- **sub-tasks:**
  - **T1.0 CHARACTERIZE** — verify EG-001 is satisfied, then pin current `DesiredConfig` parse, resolution, render, `config_digest`, and generated-schema bytes for a config without `tools` in `tests/control_plane/test_models.py` and `tests/control_plane/test_schemas.py`.
  - **T1.1 RED** — add the config, envelope, and generated-schema tests; expected failure: the model rejects `tools`, the envelopes do not exist, and schema generation emits no reference documents.
  - **T1.2 Verify RED** — run the three new files plus the two characterization files and confirm behavioral assertion failures rather than import or fixture errors.
  - **T1.3 GREEN** — implement the strict models, canonical ordering and serialization, codec/edit/migration preservation, and generated schemas, with no command behavior yet.
  - **T1.4 Verify GREEN** — rerun the targeted set plus `tests/control_plane/test_codec.py` and `tests/control_plane/test_config_edit.py`.
  - **T1.5 REFACTOR** — consolidate version, ordering, and schema-emission helpers without coupling the control plane to command execution; record `none` if no safe cleanup emerges.
  - **T1.6 Verify Task** — PV-T1-001; Ruff check and format over the touched trees; `rexec -- uv run basedpyright`; the generated-schema check; create the checkpoint.

#### T2: Discover and structurally scan identity and policy scopes

- **disposition:** active
- **outcome:** Contained discovery resolves the identity and policy scopes independently with one shared exclusion set, and one scanner turns each selected file into a typed record with one-based physical coordinates, reading no file twice.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1]
- **dependency_reason:** consumes the parsed-document and configuration models frozen by T1
- **requirements:** [FR-003, FR-007, DR-001]
- **proof:** [PV-T2-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/validate_frontmatter.py::parse_frontmatter, repo:src/project_standards/_filesystem.py::_write_bytes]
- **consumes:** [references-config-v1, the existing frontmatter parsing authority, existing containment helpers]
- **produces:** [references-parsed-document-v1]
- **preserves:** [the frontmatter parser's public semantics and error behavior; repository bytes on every discovery and scan path]
- **invariants:** [no path escapes the selected root through traversal or symlink; an excluded path is read for neither identity nor policy; each selected file is parsed at most once; coordinates are one-based and physical, not logical]
- **executor_discretion:** [internal range representation, private helper decomposition, fixture corpus layout]
- **files:** [`src/project_standards/references/discovery.py` (create; owner T2), `src/project_standards/references/markdown.py` (create; owner T2), `tests/references/conftest.py` (test; owner T2), `tests/references/test_discovery.py` (test; owner T2), `tests/references/test_markdown.py` (test; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T2 checkpoint. Never recover by widening the scanner's mention grammar, by allowing a second parse of a file, or by relaxing containment.
- **acceptance:** PV-T2-001 proves the identity and policy scopes stay distinct while sharing exclusions, traversal and symlink escapes are refused, each overlapping file is parsed once, and the scanner classifies frontmatter, inline and fenced code, link destinations, autolink targets, raw URLs, path-like tokens, reference-style links, headings, anchors, CRLF, and non-ASCII content into correct physical ranges.
- **sub-tasks:**
  - **T2.1 RED** — add discovery and scanner fixtures for split scopes, shared exclusion, traversal, symlinks, CRLF, non-ASCII, and every structural class; expected failure: no reference corpus scanner exists.
  - **T2.2 Verify RED** — run the two new files and confirm the failures are missing behavior rather than malformed fixtures.
  - **T2.3 GREEN** — implement contained discovery and the single-pass structural scanner over the existing frontmatter authority.
  - **T2.4 Verify GREEN** — targeted tests plus `tests/test_validate_frontmatter.py` and `tests/test_spec_document.py` to prove the reused authority is unchanged.
  - **T2.5 REFACTOR** — centralize byte-offset-to-physical-coordinate conversion; keep every policy decision out of the scanner.
  - **T2.6 Verify Task** — PV-T2-001; Ruff; `rexec -- uv run basedpyright`; a before/after repository-hash assertion; create the checkpoint.

#### T3: Build specification and ADR adapters and the canonical registry

- **disposition:** active
- **outcome:** One unambiguous local canonical registry is derived from nonexcluded adapter-recognized locations independently of policy `include`, with external mappings held separately and unable to shadow a local identity.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1, T2]
- **dependency_reason:** consumes references-parsed-document-v1 from T2 and the identity models frozen by T1
- **requirements:** [FR-004, FR-009, NFR-006, DR-002]
- **proof:** [PV-T3-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/validate_id.py::_ADR_ID_RE, repo:docs/adr/adr-0025-mcp-service-and-sdk-boundary.md, repo:.standards/lock.toml]
- **consumes:** [references-parsed-document-v1, references-config-v1, the existing ADR identifier grammar, the Project Specification `spec_id` pattern]
- **produces:** [references-canonical-registry-v1]
- **preserves:** [`validate_id`'s sole ownership of the ADR identifier grammar; the Project Specification and ADR schemas' own authority over declaration validity]
- **invariants:** [identity discovery never consults policy `include`; an excluded declaration creates no identity; a duplicate canonical identifier or alias collision fails closed before any consumer runs; an `external_ids` entry can never shadow a local canonical identifier]
- **executor_discretion:** [adapter protocol shape, private extraction helpers, fixture corpus layout]
- **files:** [`src/project_standards/references/identities.py` (create; owner T3), `tests/references/test_identities.py` (test; owner T3), `tests/references/fixtures` (create; owner T3)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T3 checkpoint. Never recover by widening an adapter's accepted grammar, by restating the ADR regex locally, or by resolving an ambiguous alias to a best guess.
- **acceptance:** PV-T3-001 proves `spec_id`, the canonical ADR identifier, and each accepted `ADR NNNN` / `ADR-NNNN` alias map to one document inside or outside policy `include`; case, token-boundary, near-miss, and malformed forms are nonmentions or findings as specified; duplicates and alias collisions block; and a configured external mapping resolves policy without entering the local registry.
- **sub-tasks:**
  - **T3.1 RED** — add adapter-neutral registry tests for every accepted form, boundary, case, ambiguity, external mapping, and malformed declaration; expected failure: no adapters or registry exist.
  - **T3.2 Verify RED** — targeted run; confirm the assertions fail on missing identity behavior, not fixture shape.
  - **T3.3 GREEN** — implement the adapter protocol, the spec and ADR adapters, canonical and alias collision detection, and the separate external lookup.
  - **T3.4 Verify GREEN** — targeted tests plus the existing spec, ADR, ID, and legacy reference-validator suites.
  - **T3.5 REFACTOR** — keep declaration extraction and alias grammar inside adapters; policy-facing code sees typed identities only.
  - **T3.6 Verify Task** — PV-T3-001; Ruff; `rexec -- uv run basedpyright`; create the checkpoint.

### Phase P2: Policy and Read-Only Check

#### T4: Enforce body, navigation, and local-link policy

- **disposition:** active
- **outcome:** Blocking findings are emitted for unlinked first prose references, unlinked `References` entries, incomplete configured indexes, broken local links, unknown bare local identifiers, and identifier-label target drift, while every structural and destination exemption stays silent.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T2, T3]
- **dependency_reason:** consumes references-parsed-document-v1 and references-canonical-registry-v1
- **requirements:** [FR-005, FR-006, FR-007, FR-008]
- **proof:** [PV-T4-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:docs/specs/README.md]
- **consumes:** [references-parsed-document-v1, references-canonical-registry-v1, references-config-v1]
- **produces:** [references-link-findings-v1]
- **preserves:** [the scanner's occurrence classification as the sole authority; no policy code re-matches raw text]
- **invariants:** [a configured index owns completeness for its declared namespaces and roots and an ordinary `References` heading does not; a title-only link neither mentions nor links a destination-embedded identifier; a path-like token is never a mention; historical scope is exempt from first-reference enforcement but not from broken-link checking]
- **executor_discretion:** [finding code spelling within the stable namespace, message wording inside the bounded-diagnostic rule, table-driven fixture organization]
- **files:** [`src/project_standards/references/policy.py` (create; owner T4), `tests/references/test_policy_links.py` (test; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T5]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T4 checkpoint. Never recover by downgrading an objective blocking class to advisory or by exempting a case the specification does not exempt.
- **acceptance:** PV-T4-001 proves each required, exempt, broken, wrong-target, external, anchored, ordinary-`References`, and configured-index case produces exactly the specified code, severity, and one-based physical locus, and that no exempt structural or destination occurrence is reported.
- **sub-tasks:**
  - **T4.1 RED** — add table-driven fixtures for every required, structurally exempt, destination/path exempt, broken, wrong-target, external, anchored, `References`-section, and configured-index completeness case; expected failure: no policy findings exist.
  - **T4.2 Verify RED** — targeted run; verify representative failures assert observable codes, severities, and loci rather than internal calls.
  - **T4.3 GREEN** — implement adapter-neutral body, navigation, and local-link policy with stable finding codes.
  - **T4.4 Verify GREEN** — targeted tests plus the scanner and identity suites.
  - **T4.5 REFACTOR** — deduplicate occurrence classification without widening mention grammar or absorbing editorial policy.
  - **T4.6 Verify Task** — PV-T4-001; Ruff; `rexec -- uv run basedpyright`; create the checkpoint.

#### T5: Enforce relationship and advisory policy

- **disposition:** active
- **outcome:** Schema-specific relationship values are validated in their own reference form, unresolved and noncanonical values block at the exact source field, and only the four approved advisory classes are emitted for current documents.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T3, T4]
- **dependency_reason:** consumes references-canonical-registry-v1 and extends the shared `policy.py` module T4 owns
- **requirements:** [FR-010, FR-011, FR-012]
- **proof:** [PV-T5-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/validate_references.py::build_index, repo:standards/markdown-frontmatter/versions/1.13/field-values.md]
- **consumes:** [references-canonical-registry-v1, references-link-findings-v1, existing Project Specification and Markdown Frontmatter relationship forms]
- **produces:** [references-relationship-findings-v1]
- **preserves:** [standalone `validate-references` codes, severities, and exit behavior; the distinct meaning of Project Specification `prior_specs` identifiers and Markdown Frontmatter relationship paths — neither is normalized into the other]
- **invariants:** [a superseded or historical document produces no orphan or missing-relationship advisory; an advisory never changes the exit status; an advisory never produces a reconciliation edit; only a local `prior_specs` resolution creates a `prior-spec` edge]
- **executor_discretion:** [advisory evidence helper decomposition, fixture organization]
- **files:** [`src/project_standards/references/relationships.py` (create; owner T5), `src/project_standards/references/policy.py` (modify; owner T4), `tests/references/test_policy_relationships.py` (test; owner T5)]
- **parallel_safe:** no
- **conflicts_with:** [T4]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T5 checkpoint. Never recover by normalizing one schema's reference form into the other, by promoting an advisory to blocking, or by curating `related:` to silence a finding.
- **acceptance:** PV-T5-001 proves each supported relationship form is validated in its own schema's terms; local, externally mapped, unresolved, and ambiguous `prior_specs` values have exactly the specified outcomes and edge consequences; every path defect blocks at its field with a relationship-specific code; exact-threshold and below-threshold strong-evidence cases bound the advisory; superseded and historical documents produce none; and advisory-only output still exits `0`.
- **sub-tasks:**
  - **T5.1 RED** — add relationship-form, local/external/unresolved/ambiguous prior-spec, strong-evidence threshold and below-threshold, redundancy, one-sided, orphan, superseded, and historical fixtures; expected failure: relationship policy is absent.
  - **T5.2 Verify RED** — targeted run; confirm the failures distinguish blocking resolution from advisory judgment.
  - **T5.3 GREEN** — implement schema-specific extraction and resolution plus the bounded advisory evidence rules over typed documents.
  - **T5.4 Verify GREEN** — targeted tests plus the legacy `validate-references` suite to prove standalone behavior is unchanged.
  - **T5.5 REFACTOR** — isolate relationship semantics from graph projection and reconciliation eligibility.
  - **T5.6 Verify Task** — PV-T5-001; Ruff; `rexec -- uv run basedpyright`; create the checkpoint.

#### T6: Deliver check reporting and exit contracts

- **disposition:** active
- **outcome:** `references check` accumulates every safely determinable finding, renders equivalent human and versioned JSON output, and returns the group-wide exit status, leaving the repository byte-identical.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T4, T5]
- **dependency_reason:** consumes references-link-findings-v1 and references-relationship-findings-v1
- **requirements:** [FR-013, NFR-003]
- **proof:** [PV-T6-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/cli.py::main]
- **consumes:** [references-link-findings-v1, references-relationship-findings-v1, references-finding-envelope-v1]
- **produces:** [references-check-command-v1]
- **preserves:** [existing top-level CLI help and dispatch for every other command; repository bytes on every check path]
- **invariants:** [human and JSON output carry the same semantic records; an independent finding is never suppressed by an unrelated failure; `argparse` never raises `SystemExit` across the embedding boundary]
- **executor_discretion:** [human renderer layout within the bounded-diagnostic rule, internal orchestration decomposition]
- **files:** [`src/project_standards/references/cli.py` (create; owner T6), `src/project_standards/references/reporting.py` (create; owner T6), `tests/references/test_cli_check.py` (test; owner T6), `tests/references/test_contracts.py` (test; owner T6)]
- **parallel_safe:** no
- **conflicts_with:** [T7, T8, T9]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T6 checkpoint. Never recover by parsing rendered human text to satisfy the parity assertion or by short-circuiting finding accumulation.
- **acceptance:** PV-T6-001 proves independent findings accumulate, normalized human and JSON records match semantically, advisory-only output exits `0` while blocking and internal failures exit `1` and invocation or configuration failures exit `2`, no unrelated prose is echoed, and the repository hash is unchanged before and after.
- **sub-tasks:**
  - **T6.1 RED** — add CLI and golden contract tests for clean, advisory, blocking, configuration, and internal cases plus safe finding accumulation; expected failure: the command and report surfaces do not exist.
  - **T6.2 Verify RED** — targeted run; ensure the failure is absent behavior, not `SystemExit` escaping the embedding boundary.
  - **T6.3 GREEN** — implement read-only check orchestration, reporting, JSON serialization, and the controlled error boundary.
  - **T6.4 Verify GREEN** — targeted tests plus the T2–T5 suites and top-level CLI help regressions.
  - **T6.5 REFACTOR** — share semantic record normalization between the human and JSON renderers without parsing rendered text.
  - **T6.6 Verify Task** — PV-T6-001; Ruff; `rexec -- uv run basedpyright`; a before/after repository-hash assertion; create the checkpoint.

### Phase P3: Graph and Guarded Reconciliation

#### T7: Generate deterministic local JSON and DOT graphs

- **disposition:** active
- **outcome:** `references graph` renders only validated local nodes and the six approved edge kinds as byte-deterministic JSON or DOT, to stdout by default and otherwise only to an explicitly guarded target outside both reference scopes.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T3, T4, T5]
- **dependency_reason:** consumes the validated registry and resolved relationships; an identity-invalid corpus must publish nothing
- **requirements:** [FR-014, IR-003, DR-004]
- **proof:** [PV-T7-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/_filesystem.py::_write_bytes]
- **consumes:** [references-canonical-registry-v1, references-link-findings-v1, references-relationship-findings-v1, references-graph-envelope-v1, the guarded writer]
- **produces:** [references-graph-command-v1]
- **preserves:** [the guarded writer's containment, no-follow, and atomic-replacement contract; the standards package graph as a separate model, schema, command, and vocabulary]
- **invariants:** [an unresolved or externally mapped identity is never a node or edge; edges are sorted and deduplicated; identity failure publishes nothing at all; a target inside either reference scope, a symlink, or a non-regular object is error `2`]
- **executor_discretion:** [DOT escaping helper structure, internal ordering helper names]
- **files:** [`src/project_standards/references/graph.py` (create; owner T7), `src/project_standards/references/cli.py` (modify; owner T6), `tests/references/test_graph.py` (test; owner T7), `tests/references/test_cli_graph.py` (test; owner T7)]
- **parallel_safe:** no
- **conflicts_with:** [T6, T8, T9]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T7 checkpoint. Never recover by emitting a placeholder node, by publishing a partial graph, or by relaxing an output-target guard.
- **acceptance:** PV-T7-001 proves repeated and input-permuted runs are byte-identical in both formats, all six edge kinds appear for resolved local relationships, unresolved and externally mapped identities produce neither nodes nor edges, an identity-invalid corpus publishes nothing, symlinked/non-regular/identity-scope/policy-scope targets fail as error `2` unchanged, and a valid publication alters only its named target.
- **sub-tasks:**
  - **T7.1 RED** — add graph model, edge, ordering, DOT, and output-path tests including symlink, directory, and in-scope targets; expected failure: the graph command and builder are absent.
  - **T7.2 Verify RED** — targeted run; confirm the observable graph and output assertions fail.
  - **T7.3 GREEN** — implement the graph projection and renderers plus guarded publication through the existing filesystem primitives.
  - **T7.4 Verify GREEN** — targeted tests plus policy, contract, and filesystem regressions.
  - **T7.5 REFACTOR** — centralize the stable ordering and escaping shared by JSON and DOT without introducing persistent state.
  - **T7.6 Verify Task** — PV-T7-001; Ruff; `rexec -- uv run basedpyright`; stdout repository-hash and explicit-target effect assertions; create the checkpoint.

#### T8: Plan only allowlisted reconciliation edits

- **disposition:** active
- **outcome:** `references reconcile` emits a deterministic read-only typed preview containing only uniquely determined visible-label edits, each digest-bound and nonoverlapping, and never a destination, URL, path, ambiguous, or editorial change.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T4, T5, T6]
- **dependency_reason:** converts the stable finding codes produced by T4/T5 and rendered by T6 into edits
- **requirements:** [FR-016, FR-017, DR-005]
- **proof:** [PV-T8-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements]
- **consumes:** [references-link-findings-v1, references-relationship-findings-v1, references-check-command-v1, references-plan-envelope-v1]
- **produces:** [references-reconcile-preview-v1]
- **preserves:** [authored bytes on every preview path; the advisory classes' immunity from repair]
- **invariants:** [eligibility is exhaustive over stable finding codes, so a new code is ineligible until explicitly admitted; spans are bounded and nonoverlapping; a preview is informative output and never an apply token]
- **executor_discretion:** [span construction helper structure, preview rendering layout]
- **files:** [`src/project_standards/references/reconcile.py` (create; owner T8), `src/project_standards/references/cli.py` (modify; owner T6), `tests/references/test_reconcile_plan.py` (test; owner T8)]
- **parallel_safe:** no
- **conflicts_with:** [T6, T7, T9]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T8 checkpoint. Never recover by widening the eligibility allowlist to clear a real finding or by planning an edit whose target is not uniquely determined.
- **acceptance:** PV-T8-001 proves safe visible-label positives yield the exact span, replacement, and source digest; destination, autolink, URL, path-like, ambiguous, editorial, and historical cases yield no plan entry; overlapping spans are refused; and repeated preview over unchanged bytes is byte-identical and leaves the repository unchanged.
- **sub-tasks:**
  - **T8.1 RED** — add exact preview and mutation-allowlist tests including destination, path, ambiguity, and overlapping-span refusal; expected failure: the planner is absent.
  - **T8.2 Verify RED** — targeted run; confirm the failures assert plan content rather than mock invocation.
  - **T8.3 GREEN** — implement finding-to-edit planning and preview reporting only; no write path.
  - **T8.4 Verify GREEN** — targeted tests plus the link, relationship, and contract suites.
  - **T8.5 REFACTOR** — keep span construction pure and make eligibility exhaustive over the stable finding-code set.
  - **T8.6 Verify Task** — PV-T8-001; Ruff; `rexec -- uv run basedpyright`; a byte-idempotence assertion; create the checkpoint.

#### T9: Apply plans through guarded per-file replacement

- **disposition:** active
- **outcome:** `reconcile --apply` rescans, recomputes and emits its own plan, verifies containment and every content digest as a group before the first write, then replaces each planned target atomically and reports applied and unapplied targets honestly.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T8]
- **dependency_reason:** consumes references-reconcile-preview-v1 as the plan shape it recomputes and publishes
- **requirements:** [FR-015, FR-018, FR-019, IR-004]
- **proof:** [PV-T9-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#71-functional-requirements, repo:src/project_standards/_filesystem.py::_write_bytes, repo:src/project_standards/control_plane/executor.py::apply_reconciliation]
- **consumes:** [references-reconcile-preview-v1, the guarded writer's replace, no-follow, mode, and cleanup behavior]
- **produces:** [references-reconcile-apply-v1]
- **preserves:** [the guarded writer's public contract and the existing control-plane executor's behavior; every target byte when preflight fails]
- **invariants:** [no byte is written until the whole plan passes containment and digest preflight; each individual target is replaced atomically or not at all; no prior preview is accepted as input; remaining blocking findings still produce exit `1` after a successful apply]
- **executor_discretion:** [apply-report structure, internal cleanup helper decomposition]
- **files:** [`src/project_standards/references/application.py` (create; owner T9), `src/project_standards/references/cli.py` (modify; owner T6), `tests/references/test_reconcile_apply.py` (test; owner T9), `tests/test_filesystem.py` (modify; owner T9)]
- **parallel_safe:** no
- **conflicts_with:** [T6, T7, T8]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T9 checkpoint and restore any fixture corpus from its recorded pre-apply digests. Never recover by weakening a precondition, by writing before group preflight, or by claiming a rollback the writer does not provide.
- **acceptance:** PV-T9-001 proves a stale or unsafe plan exits nonzero with every target byte unchanged, each successful target is atomically replaced, an injected later-file failure reports applied and unapplied targets without a transaction claim, an interrupted run leaves no truncated target, and remaining blocking findings still drive exit `1`.
- **sub-tasks:**
  - **T9.0 CHARACTERIZE** — pin the existing guarded writer's replace, no-follow, mode, and cleanup behavior that the application boundary depends on.
  - **T9.1 RED** — add apply, stale-digest, symlink, concurrent-change, partial-publication, interruption, and status tests; expected failure: no apply orchestration exists.
  - **T9.2 Verify RED** — targeted run; confirm no wrong-reason filesystem setup failures.
  - **T9.3 GREEN** — implement full-plan preflight and atomic per-file publication using the existing guarded primitives only.
  - **T9.4 Verify GREEN** — targeted tests plus the shared filesystem and control-plane executor regressions.
  - **T9.5 REFACTOR** — centralize apply reporting and cleanup without adding rollback or persistent plan state.
  - **T9.6 Verify Task** — PV-T9-001; Ruff; `rexec -- uv run basedpyright`; interruption and no-truncation assertions; create the checkpoint.

### Phase P4: Aggregate Integration, Distribution, and Dogfood Adoption

#### T10: Compose opt-in aggregate validation

- **disposition:** active
- **outcome:** `project-standards validate` runs the reference checker only when `[tools.references].enabled = true`, and an overlapping defect appears from both the legacy pass and the new checker with distinct codes, severities, and source attribution.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T1, T6]
- **dependency_reason:** consumes references-config-v1 for the gate and references-check-command-v1 for the contribution
- **requirements:** [FR-002, FR-020, IR-006]
- **proof:** [PV-T10-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#73-interface-requirements, repo:src/project_standards/cli.py::main, repo:src/project_standards/validate_references.py::build_index, repo:tests/control_plane/test_models.py::test_desired_config_is_strict_frozen_and_deterministically_ordered]
- **consumes:** [references-config-v1, references-check-command-v1, the existing aggregate dispatch and its result composition]
- **produces:** [references-aggregate-contribution-v1]
- **preserves:** [standalone `validate-references`, `validate-frontmatter`, `validate-id`, control-plane validation, and standards-graph codes, severities, ordering, and exit behavior; the aggregate's behavior for every repository that does not enable the tool]
- **invariants:** [no standards-package selection can enable the contribution; the disabled path performs no scan and emits no finding; overlapping findings are attributed, never merged or reclassified]
- **executor_discretion:** [lazy-import structure, internal result-composition helpers]
- **files:** [`src/project_standards/cli.py` (modify; owner T10), `src/project_standards/control_plane/models.py` (modify; owner T1), `tests/references/test_aggregate.py` (test; owner T10), `tests/test_validate_references.py` (modify; owner T10)]
- **parallel_safe:** no
- **conflicts_with:** [T11]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T10 checkpoint; the aggregate returns to its characterized behavior. Never recover by silencing a legacy finding, by deduplicating an overlap, or by coupling the gate to a package selection.
- **acceptance:** PV-T10-001 proves an absent or disabled configuration emits no reference finding and performs no scan, an enabled configuration runs the checks, an overlapping metadata defect retains both contributors' distinct codes, severities, and source attribution, and every legacy validator and standards-graph suite is unchanged.
- **sub-tasks:**
  - **T10.0 CHARACTERIZE** — pin the current aggregate and standalone exit status, ordering, and legacy warning behavior on an overlapping metadata defect.
  - **T10.1 RED** — add enabled, disabled, and overlap aggregate tests; expected failure: aggregate dispatch ignores the tools namespace.
  - **T10.2 Verify RED** — targeted run; confirm the disabled characterization stays green while the enabled assertions fail.
  - **T10.3 GREEN** — add lazy opt-in dispatch and attributed result composition without changing any legacy provider's behavior.
  - **T10.4 Verify GREEN** — targeted tests plus all legacy validate, control-plane, and standards-graph suites.
  - **T10.5 REFACTOR** — isolate aggregate selection from package resolution so no standard selection can reach the gate.
  - **T10.6 Verify Task** — PV-T10-001; Ruff; `rexec -- uv run basedpyright`; the aggregate help regression; create the checkpoint.

#### T11: Prove top-level and wheel distribution parity

- **disposition:** active
- **outcome:** `project-standards references {check,graph,reconcile}` is available and behaviorally identical from the source tree, the candidate wheel, and an installed wheel, with no selected standards package and no MCP configuration present.
- **work_type:** brownfield-behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** public
- **depends_on:** [T6, T7, T9, T10]
- **dependency_reason:** parity can only be proven once all three subcommands and the aggregate contribution exist
- **requirements:** [FR-001, NFR-004, IR-001]
- **proof:** [PV-T11-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#73-interface-requirements, repo:src/project_standards/cli.py::main, repo:tests/test_installed_wrappers.py::installed_venv, repo:tests/package_compatibility/matrix.py::LifecycleResult, repo:pyproject.toml, repo:README.md]
- **consumes:** [references-check-command-v1, references-graph-command-v1, references-reconcile-apply-v1, references-aggregate-contribution-v1, the existing installed-wheel probe harness and compatibility matrix]
- **produces:** [references-cli-group-v1]
- **preserves:** [existing wrapper and compatibility-matrix results; lazy import cost for unrelated commands; the absence of any MCP or standards-selection import on the references path]
- **invariants:** [help exposes exactly the three approved v1 subcommands; normalized JSON and exit status match across all three distributions; no package selection is required for availability]
- **executor_discretion:** [probe helper decomposition, packaging-data declaration details]
- **files:** [`src/project_standards/cli.py` (modify; owner T10), `pyproject.toml` (modify; owner T11), `tests/references/test_distribution.py` (test; owner T11), `tests/test_installed_wrappers.py` (modify; owner T11), `tests/package_compatibility` (modify; owner T11)]
- **parallel_safe:** no
- **conflicts_with:** [T10]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T11 checkpoint. Never recover by narrowing a probe to the distribution that happens to pass or by importing MCP or standards-selection code to make a path resolve.
- **acceptance:** PV-T11-001 proves `--help` exposes exactly `check`, `graph`, and `reconcile`; normalized JSON output and exit status are identical from source, candidate wheel, and installed wheel; the commands remain available with no selected standard and no MCP configuration; and the existing wrapper and compatibility-matrix suites stay green.
- **sub-tasks:**
  - **T11.1 RED** — add source, candidate, and installed availability and parity probes; expected failure: top-level dispatch and the wheel lack the group.
  - **T11.2 Verify RED** — run the source-focused probes first and confirm the missing command, not candidate setup failure, is the cause.
  - **T11.3 GREEN** — add lazy top-level dispatch and any required package-data or schema projection.
  - **T11.4 Verify GREEN** — targeted source tests, then build and extract the candidate wheel per `README.md` and run the candidate and installed probes.
  - **T11.5 REFACTOR** — keep MCP imports and standards selection out of the references import path.
  - **T11.6 Verify Task** — PV-T11-001; Ruff; `rexec -- uv run basedpyright`; the compatibility subset; create the checkpoint.

#### T12: Reconcile and enable the dogfood corpus

- **disposition:** active
- **outcome:** This repository declares an honest `[tools.references]` scope, its recorded full-corpus baseline is remediated to zero blocking findings through reviewed safe reconciliation and manual objective fixes, `docs/specs/README.md` covers its declared namespaces and roots, and the aggregate gate is enabled only after that is true.
- **work_type:** transition
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** deployment
- **depends_on:** [T10, T11]
- **dependency_reason:** requires the aggregate gate and a qualified candidate wheel before this repository's own corpus may be measured and enabled
- **requirements:** [REQ-001]
- **proof:** [PV-T12-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#182-configuration, repo:.standards/config.toml, repo:docs/specs/README.md, repo:docs/adr/adr-0025-mcp-service-and-sdk-boundary.md, repo:scripts/verify.sh, repo:AGENTS.md, repo:README.md]
- **consumes:** [references-aggregate-contribution-v1, references-cli-group-v1, references-reconcile-apply-v1, this repository's authored Markdown corpus]
- **produces:** [dogfood-reference-scope-v1, the Appendix C dogfood corpus baseline]
- **preserves:** [the authored meaning of every edited document; the advisory inventory as advisory; every unrelated `.standards/config.toml` key and its rendering]
- **invariants:** [no waiver or suppression mechanism is introduced; scope is never narrowed to hide known drift; the preview is reviewed before any apply; every non-mechanical edit is classified before mutation; the aggregate gate is enabled only after the declared scope is clean]
- **executor_discretion:** [order of manual remediation, wording of prose corrections that preserve meaning, scratch log organization]
- **files:** [`.standards/config.toml` (modify; owner T12), `docs/specs/README.md` (modify; owner T12), `docs/**/*.md` (modify as reported and reviewed; owner T12), `tests/references/test_repository_corpus.py` (test; owner T12)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** abort before mutation if the baseline cannot be attributed to policy drift; on apply failure, restore the affected documents from their recorded pre-apply digests and rerun `check`. Never recover by adding a waiver, by excluding a path that has real drift, or by leaving the aggregate gate enabled over a scope with blocking findings.
- **acceptance:** PV-T12-001 proves the declared scope is nonempty and honest, the baseline is recorded before any edit, the reviewed preview is applied without editorial changes, the remediated corpus produces zero blocking findings under the candidate runtime, `docs/specs/README.md` covers its declared namespaces and roots including SPEC-GSF3, the advisory inventory is asserted structurally rather than by pinned count, and no waiver or suppression key exists.
- **sub-tasks:**
  - **T12.1 PRECHECK** — build and extract the candidate wheel per `README.md`, run the full-corpus check, and record the blocking and advisory baseline at its Appendix C path before any edit.
  - **T12.2 PROVE ABSENCE** — add structural corpus assertions that fail on duplicate identities, missing configured-index coverage, or a scope narrowed to hide drift, and confirm each failure is policy drift rather than a configuration, parser, or environment defect.
  - **T12.3 APPLY** — review the reconciliation preview, apply only allowlisted edits, perform reviewed manual fixes for the remaining objective findings, index SPEC-GSF3, and write the honest tool configuration; never auto-curate a relationship.
  - **T12.4 VERIFY** — rerun the corpus tests, `references check`, `spec validate`, `spec lint`, the `AGENTS.md` Prettier and markdownlint gate over changed documents, and `git diff --check`.
  - **T12.5 PROVE IDEMPOTENCY** — rerun reconciliation and confirm an empty plan, then enable the aggregate gate and confirm `project-standards validate` is clean under the candidate runtime.
  - **T12.6 Verify Task** — PV-T12-001; `rexec -- ./scripts/verify.sh`; create the checkpoint with the exact changed-document inventory.

### Phase P5: Hardening, Documentation, and Qualification

#### T13: Harden security, determinism, and failure boundaries

- **disposition:** active
- **outcome:** Containment, symlink and TOCTOU resistance, reference-scope output refusal, network denial, bounded diagnostics, deterministic ordering, absence of persistent state, and the complete ERR-001–ERR-008 exit classification are proven under adversarial input, with the accepted no-hard-resource-cap boundary recorded rather than silently fixed.
- **work_type:** behavior
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T7, T9, T10]
- **dependency_reason:** the adversarial matrix needs every read path, the mutation path, and the aggregate gate to exist
- **requirements:** [NFR-001, NFR-002, NFR-007, IR-002, DR-006]
- **proof:** [PV-T13-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#72-non-functional-requirements, repo:src/project_standards/_filesystem.py::_write_bytes]
- **consumes:** [references-check-command-v1, references-graph-command-v1, references-reconcile-apply-v1, references-aggregate-contribution-v1]
- **produces:** [references-safety-matrix-v1, the Appendix C security review receipt]
- **preserves:** [all frozen behavior from T1–T12; no unplanned hardening change is made inside this verification task]
- **invariants:** [each assertion is first proven to reject an injected wrong result before it is run against the real implementation; a real gap becomes an appended correction task, never an inline fix; no numeric resource limit is invented]
- **executor_discretion:** [fault-injection technique, parametrization structure, mutation-control organization]
- **files:** [`tests/references/test_security.py` (test; owner T13), `tests/references/test_invariants.py` (test; owner T13)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T13 checkpoint. Never recover by weakening an assertion, by deleting an adversarial case, or by fixing production code inside this task instead of appending a correction task.
- **acceptance:** PV-T13-001 proves parametrized path, encoding, and ordering inputs preserve every determinism and containment invariant; socket APIs are denied on all read paths; an invalid graph target leaves the target unchanged at exit `2`; an injected failure leaves no partial output; the status matrix covers ERR-001 through ERR-008; diagnostics omit unrelated document text; no persistent state is written; and no unsupported numeric resource limit was introduced.
- **sub-tasks:**
  - **T13.1 RED** — add adversarial parametrized invariants and mutation-sensitive plausible-wrong-output cases; first prove each assertion detects its injected wrong result rather than requiring correct production code to fail.
  - **T13.2 Verify RED** — run the mutation and fault-injection controls, then the real implementation; if the real implementation fails, confirm the intended safety or determinism gap and append a correction task before changing production code.
  - **T13.3 GREEN** — complete the acceptance matrix; any real gap is implemented only in its separately appended correction task.
  - **T13.4 Verify GREEN** — targeted security and invariant tests plus the whole references suite.
  - **T13.5 REFACTOR** — consolidate the error taxonomy and safety helpers only where observable behavior stays frozen.
  - **T13.6 Verify Task** — PV-T13-001; `rexec -- uv run pytest tests/references`; Ruff; `rexec -- uv run basedpyright`; network-denied execution; create the checkpoint.

#### T14: Record performance, document, and qualify release

- **disposition:** active
- **outcome:** A reproducible cold-run benchmark is on record, the optional-tooling documentation set is accurate and exercised against candidate bytes, the change is classified under `meta/versioning.md`, and the full repository and three-distribution gates pass; publication remains separately authorized.
- **work_type:** documentation
- **checkpoint:** one green commit with task, requirement, proof IDs, and the required `Plan-*` checkpoint trailers
- **boundary:** deployment
- **depends_on:** [T11, T12, T13]
- **dependency_reason:** the benchmark and documentation describe a distribution-qualified, dogfooded, hardened subsystem
- **requirements:** [NFR-005, REQ-002]
- **proof:** [PV-T14-001]
- **source_refs:** [spec:docs/specs/2026-07-31-durable-document-references-optional-tooling-spec.md#187-documentation-deliverables, repo:meta/versioning.md, repo:README.md, repo:scripts/verify.sh, repo:AGENTS.md]
- **consumes:** [references-cli-group-v1, dogfood-reference-scope-v1, references-safety-matrix-v1]
- **produces:** [reference-tooling-documentation-v1, the Appendix C cold-run benchmark record]
- **preserves:** [existing README and package-reference content for unrelated features; the versioning policy itself unless a clarification is genuinely required]
- **invariants:** [no numeric performance threshold is invented; no corpus count is hardcoded; every documented command is executed against candidate bytes; documentation states that neither standards adoption nor MCP enables or owns the feature]
- **executor_discretion:** [document structure and section ordering, benchmark harness internals]
- **files:** [`docs/reference-tooling.md` (create; owner T14), `README.md` (modify; owner T14), `src/project_standards/README.md` (modify; owner T14), `tests/references/test_performance.py` (test; owner T14), `tests/references/test_documentation.py` (test; owner T14)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** revert the T14 checkpoint. Never recover by relaxing a documented example to match a defect, by hardcoding a corpus count to stabilize the benchmark, or by publishing without separate authorization.
- **acceptance:** PV-T14-001 proves the benchmark record states environment, corpus shape, method, and observed result without hardcoded counts and is reproducible; every documented command and example runs against candidate bytes with the documented result; the documentation distinguishes explicit availability, aggregate opt-in, standards adoption, and MCP; the versioning classification is recorded; and `scripts/verify.sh --full` plus the three-distribution probes pass.
- **sub-tasks:**
  - **T14.1 RED** — add the benchmark harness contract and the documentation example and inventory checks; expected failure: the benchmark record and documents are absent.
  - **T14.2 Verify RED** — confirm the failures are missing deliverables rather than environment setup.
  - **T14.3 GREEN** — record the benchmark at its Appendix C path, author the documentation set, and apply the `meta/versioning.md` classification without publishing.
  - **T14.4 Verify GREEN** — run the targeted documentation and benchmark tests, then execute every documented command against candidate bytes.
  - **T14.5 REFACTOR** — remove duplicated documentation while keeping one human landing summary and one detailed guide.
  - **T14.6 Verify Task** — PV-T14-001; rebuild and extract the candidate wheel per `README.md`; `rexec -- ./scripts/verify.sh --full`; the package contract gates; candidate dogfood validation; installed-wheel parity; the `AGENTS.md` Prettier and markdownlint gate; `git diff --check`; create the checkpoint. Release publication remains separately authorized.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. Answer OQ-001 and satisfy EG-001, then freeze the configuration and envelope contracts (T1); gate: PV-T1-001 plus unchanged rendering and `config_digest` for configs without `[tools]`.
2. Build discovery, the scanner, the adapters, and the canonical registry (T2, T3); gate: PV-T2-001 and PV-T3-001 with the registry failing closed on ambiguity.
3. Add link, navigation, relationship, and advisory policy and the read-only `check` (T4, T5, T6); gate: PV-T4-001, PV-T5-001, PV-T6-001 with a byte-unchanged repository.
4. Add the graph and preview-first reconciliation, then guarded apply (T7, T8, T9); gate: PV-T7-001, PV-T8-001, PV-T9-001 with group preflight proven before any write.
5. Compose the opt-in aggregate contribution (T10); gate: PV-T10-001 with every legacy suite unchanged.
6. Qualify distribution across source, candidate, and installed wheels (T11); gate: PV-T11-001.
7. Baseline, remediate, and enable this repository's dogfood scope (T12); gate: PV-T12-001 with the Appendix C dogfood corpus baseline recorded before any edit.
8. Harden, benchmark, document, classify, and run the full gate (T13, T14); gate: PV-T13-001, PV-T14-001, and `scripts/verify.sh --full`. Publication is a separately authorized step outside this plan.

### 10.2 Migration / State / Configuration Transition

- Required: yes — authored-document drift and one consumer configuration only. The subsystem owns no persistent state, so nothing else migrates.
- Compatibility period: indefinite. A repository without `[tools.references]` keeps its current parse, render, digest, and aggregate behavior forever; the feature is disabled by default.
- Idempotency: reconciliation converges — after the safe edits are applied, a rerun produces an empty plan. Enabling the aggregate gate is a single declarative configuration key.
- Point of no return: none within this plan. The first `reconcile --apply` in T12 is the only durable document mutation, and it is reviewed, digest-preconditioned, and revertible through Git.
- Rollback / forward repair: revert the owning task's checkpoint. For T12, restore affected documents from their recorded pre-apply digests and rerun `check`; recovery is forward — inspect current bytes and compute a new plan, never replay an old one.
- Recovery proof: PV-T9-001 (group preflight leaves every target byte unchanged; an induced later-file failure reports applied and unapplied targets) and PV-T12-001 (post-remediation rerun yields an empty plan).

### 10.3 Late Failure and Correction

If T13's adversarial matrix or T14's final gate exposes a defect in already-completed work, the verification task blocks at that point. The executor appends a new correction task with permanent new IDs carrying `corrects:` and `discovered_from:`, runs `sync`, completes the correction with its own checkpoint, and reruns the blocked verification from its anchor. Completed tasks are immutable execution history and are never silently reopened or rewritten. If the failure instead shows that the governing authority changed — for example an owner decision that alters an unfinished acceptance target — the executor drains in-progress work, runs `pause`, creates a revision draft with `revise`, and activates it with `replace`, using reciprocal `supersedes` / `superseded_by` declarations rather than repurposing an existing task ID.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | The structural scanner misclassifies code or link spans and floods the corpus with blocking noise. | medium | high | Physical-range fixtures and near-miss mutation cases land before any policy code; policy may not re-match raw text. | T2, T4 |
| R-002 | Config rendering drops or rewrites consumer-owned tool data. | medium | high | Brownfield round-trip characterization before the change plus a generated-schema and `config_digest` assertion for configs without `[tools]`. | T1 |
| R-003 | New aggregate findings obscure legacy severity or source. | medium | medium | Distinct stable code namespaces plus an explicit overlapping-defect fixture asserting both contributors' attribution. | T10 |
| R-004 | Reconciliation overwrites concurrent or user edits. | low | high | Complete containment and digest preflight before the first write; apply always recomputes its own plan. | T9 |
| R-005 | Dogfood adoption expands into unbounded editorial cleanup. | medium | high | Safe allowlist, exact recorded baseline, objective-only manual fixes, and no waiver mechanism. | T12 |
| R-006 | Source behavior differs from packaged or installed behavior. | medium | high | Three-distribution normalized parity probes and candidate-first documentation examples. | T11, T14 |
| R-007 | Pathological repository-owned Markdown stalls or exhausts a validation run. | low | medium | Accepted v1 risk per SPEC-GSF3 A-001: malformed-input coverage and a reproducible benchmark, with evidence-based limits only in a later revision. | T13, T14 |
| R-008 | OQ-001 is answered after T1 has already frozen the configuration contract, forcing a schema revision mid-plan. | medium | medium | EG-001 blocks T1 until the decision exists; the decision is recorded in SPEC-GSF3's revision log before implementation. | Owner / T1 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | Repository-scale authored Markdown can be scanned on demand without a persistent cache or a hard resource cap. | A pathological corpus could stall CI; v1 accepts the risk, records the Appendix C cold-run benchmark, and reconsiders WH-002 or evidence-based limits in a later specification revision. |
| A-002 | The existing frontmatter and Markdown parsing surfaces can expose ranges, links, headings, and relationship fields without changing their owners' semantics. | A shared parsing boundary must be introduced without duplicating a grammar or weakening an existing validator, which enlarges T2 and may require a correction task against `validate_frontmatter`. |
| A-003 | This repository's real corpus contains no duplicate canonical identifier or alias collision that only a policy change could resolve. | T12's baseline would surface an identity conflict requiring an authored-document decision by the owner before remediation can proceed. |
| A-004 | SPEC-GSF3 remains at `status: draft` while this plan executes, and its draft contract is a sufficient authority for implementation. | If the owner approves or materially revises the specification mid-execution, the executor drains work and runs the pause/revise/replace transaction rather than absorbing the change silently. |

### 11.3 Open Questions

| Question | Blocking? | Owner | Current Assumption |
| --- | --- | --- | --- |
| Does introducing the sibling `[tools]` table require the consumer-config header to advance to `schema_version = "1.2"`? Tracked as SPEC-GSF3 OQ-001. | No for the plan; EG-001 blocks T1 alone until it is answered. | Owner | Follow the repository's `role` precedent: gate writing the namespace behind a new header version, keep every prior header valid, and exclude the absent namespace from the digest basis. |
| Will this repository's real corpus reveal ambiguous or editorial findings outside the safe repair allowlist? | No | Owner | Record them as advisories or deferred work; do not mutate or block release unless they are objectively blocking under the specification. |

## 12. Final Verification

- Every Must requirement in §6 maps to a completed owning task and a passing Appendix B proof; no accepted behavior depends on a hardcoded corpus count.
- All fourteen tasks are `done` or explicitly `skipped` with recorded evidence, and no blocker or unresolved correction task remains.
- The candidate wheel is built and extracted exactly as `README.md` documents, and `build/wheel-runtime` is first on `PYTHONPATH` for every dogfood check.
- `rexec -- ./scripts/verify.sh --full` passes after the final content change.
- `uv run project-standards standards validate-packages --root . --json`, `standards validate-graph --root . --require-all-manifests --json`, `standards generate-package-schemas --root . --check`, and `standards sync-payload-projection --root . --check` pass.
- Candidate `project-standards validate`, `references check`, graph determinism, and reconcile preview pass against the enabled dogfood scope.
- Source, candidate, and installed normalized CLI probes pass with no selected standards package and no MCP configuration.
- `uv run ruff check .`, `uv run ruff format --check .`, `rexec -- uv run basedpyright`, and `uv run pip-audit` pass.
- The `AGENTS.md` Prettier and markdownlint invocations pass over the Git-tracked scope, and `git diff --check` is clean.
- All three Appendix C records exist at their committed paths, are sanitized, and are referenced from the close-out record.
- SPEC-GSF3 §17.3 is current, its Deviations Log has an owner disposition for every entry, and OQ-001 is answered.
- Release, tag, and publication occur only under their own separate authorizations.

## 13. Close-out

- **Completed:** pending.
- **Decisions / deviations harvested:** pending — harvest into SPEC-GSF3 §8.3, its Deviations Log, and ADRs where a decision outlives the plan.
- **Risks closed / accepted:** pending — R-007's accepted resource-limit boundary must be restated in the released documentation, not only here.
- **Deferred/discovered work filed:** pending — Appendix D items become issues before the session ends.
- **Source/ADR/handoff reconciliation:** pending — update `docs/handoff/specs-plans.md`, SPEC-GSF3 `status`/`last_reviewed`, and issue #178.
- **Scratch teardown:** only after all three Appendix C records are committed outside `.project-pipeline/`.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `references-config-v1` | T1 | T2, T6, T10, T12 | `.standards/config.toml` admits only `project_standards` and `standards` | Closed optional `[tools.references]` with `enabled`, `include`, `exclude`, `historical`, `indexes`, `namespaces`, `external_ids` | Unknown key or empty effective scope is error `2` | Configs omitting `[tools]` render byte-identically with an unchanged `config_digest`; header versioning follows OQ-001 | SPEC-GSF3 IR-005 |
| `references-parsed-document-v1` | T2 | T3, T4, T5, T7, T8 | absent | Path, identity, title, kind, status, structural ranges, links, mentions, relationships | Unreadable or malformed governed document fails identity-dependent output | One record per selected regular file; contained path; one-based physical coordinates | SPEC-GSF3 DR-001 |
| `references-canonical-registry-v1` | T3 | T4, T5, T7, T8 | absent | Canonical identifier and accepted aliases to exactly one local document; external mappings held separately | Duplicate identifier or alias collision blocks and refuses graph and reconciliation | An external mapping can never shadow a local identity or become a node | SPEC-GSF3 DR-002, FR-009 |
| `references-finding-envelope-v1` | T1 | T6, T10 | absent | Schema version, stable code, severity, path, physical locus, message, guidance | Closed envelope; unknown envelope version rejected | Deterministic order; human and JSON carry the same semantic records | SPEC-GSF3 DR-003, NFR-003 |
| `references-graph-envelope-v1` | T1 | T7 | absent | Versioned nodes and typed edges; DOT is a deterministic rendering of it | Identity failure publishes nothing | Unresolved and externally mapped identities are neither nodes nor edges; edges sorted and deduplicated | SPEC-GSF3 DR-004, IR-003 |
| `references-plan-envelope-v1` | T1 | T8, T9 | absent | Repository identity, target files, source digests, ordered nonoverlapping span edits | Stale digest or unsafe path fails before any write | Preconditions are mandatory; a preview is never an apply token | SPEC-GSF3 DR-005, IR-004 |
| `references-cli-group-v1` | T11 | operators, CI, T12 | absent | `references {check,graph,reconcile}` in the main wheel | Exit `0` success including advisory-only, `1` policy/identity/publication/precondition/apply/internal, `2` invocation/configuration | Available without any selected standard or MCP; identical across source, candidate, and installed | SPEC-GSF3 IR-001, IR-002 |
| `references-aggregate-contribution-v1` | T10 | `project-standards validate` | Frontmatter, ID, metadata-reference, control-plane contributors | One additional contributor gated solely on `[tools.references].enabled` | Disabled path performs no scan and emits nothing | Legacy codes, severities, and exits unchanged; overlaps attributed, never merged | SPEC-GSF3 FR-002, FR-020, IR-006 |
| `dogfood-reference-scope-v1` | T12 | this repository's CI | No tool scope declared | Honest declared scope with the aggregate gate enabled after remediation | Enabling over a scope with blocking findings is a defect | No waiver or suppression mechanism; scope never narrowed to hide drift | SPEC-GSF3 §18.2 |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | IR-005, DR-003 | T1 | contract and brownfield regression | The pre-change `DesiredConfig` render bytes and `config_digest`; the frozen envelope JSON Schemas | `uv run pytest tests/references/test_config.py tests/references/test_models.py tests/references/test_schemas.py tests/control_plane/test_models.py tests/control_plane/test_schemas.py tests/control_plane/test_codec.py tests/control_plane/test_config_edit.py`, then `uv run project-standards standards generate-package-schemas --root . --check` | Approved keys round-trip canonically; unknown keys and an empty effective scope are rejected with bounded diagnostics; the three envelopes reject extra fields and serialize byte-identically under permuted semantically-equal input; a config without `[tools]` renders byte-identically with an unchanged digest | Add an undeclared key and expect acceptance; permute input ordering and expect differing bytes; drop the `[tools]` table during a standards-only edit and expect it to survive; declare an empty effective scope and expect exit `0` | local | ephemeral |
| PV-T2-001 | FR-003, FR-007, DR-001 | T2 | unit over a synthetic corpus | The specification's exemption list; a before/after repository content hash | `uv run pytest tests/references/test_discovery.py tests/references/test_markdown.py tests/test_validate_frontmatter.py tests/test_spec_document.py` | Identity and policy scopes stay distinct while sharing exclusions; traversal and symlink escapes are refused; each overlapping file is parsed once; every structural, destination, path-like, CRLF, and non-ASCII class lands in the correct physical range; the repository hash is unchanged | A scanner that treats a link destination or an `adr-0025-...` filename as visible prose; an excluded path that still yields a parsed record; a symlink that resolves outside the root; a second parse of an overlapping file | local | ephemeral |
| PV-T3-001 | FR-004, FR-009, NFR-006, DR-002 | T3 | unit with adapter substitution | `validate_id._ADR_ID_RE`; the Project Specification `spec_id` pattern; this repository's real 32-document ADR corpus | `uv run pytest tests/references/test_identities.py tests/test_validate_id.py tests/test_validate_references.py` | Each accepted specification and ADR form and alias maps to one document inside or outside policy `include`; case, boundary, near-miss, and malformed forms behave as specified; duplicates and alias collisions block; external mappings resolve policy without entering the registry | An `external_ids` entry that shadows a local canonical identifier; a lowercase or unbounded token accepted as a mention; an excluded declaration that creates an identity; an ambiguous numeric alias resolved to a best guess; a locally restated ADR regex | local | ephemeral |
| PV-T4-001 | FR-005, FR-006, FR-007, FR-008 | T4 | table-driven unit | The specification's FR-005–FR-008 acceptance criteria and EC-003, EC-004, EC-005, EC-014, EC-015, EC-017 | `uv run pytest tests/references/test_policy_links.py tests/references/test_markdown.py tests/references/test_identities.py` | Every required, exempt, broken, wrong-target, external, anchored, ordinary-`References`, and configured-index case yields exactly the specified code, severity, and one-based locus, and no exempt occurrence is reported | A policy pass that enforces completeness on an ordinary `References` heading; a title-only link counted as linking its destination-embedded identifier; a path-like token reported as a bare mention; a resolving link to the wrong document accepted | local | ephemeral |
| PV-T5-001 | FR-010, FR-011, FR-012 | T5 | table-driven unit plus legacy regression | The Project Specification `prior_specs` and Markdown Frontmatter relationship forms; the pre-change standalone `validate-references` output | `uv run pytest tests/references/test_policy_relationships.py tests/test_validate_references.py` | Each relationship form is validated in its own schema's terms; local, external, unresolved, and ambiguous `prior_specs` values have exactly the specified outcomes and edge consequences; path defects block at their field; exact-threshold and below-threshold advisories are bounded; superseded and historical documents produce none; advisory-only output exits `0` | Normalizing a `prior_specs` identifier into a path or vice versa; promoting an advisory to blocking; emitting an orphan advisory for a superseded document; creating a `prior-spec` edge from an externally mapped value; a changed legacy code or severity | local | ephemeral |
| PV-T6-001 | FR-013, NFR-003 | T6 | integration and golden contract | The frozen finding envelope; normalized semantic record comparison rather than rendered-text parsing; a before/after repository hash | `uv run pytest tests/references/test_cli_check.py tests/references/test_contracts.py` and the top-level CLI help regression | Independent findings accumulate; normalized human and JSON records match; advisory-only exits `0`, blocking and internal exit `1`, invocation and configuration exit `2`; no unrelated prose is echoed; the repository hash is unchanged | A renderer whose parity is achieved by parsing its own human output; a run that stops at the first finding; an `argparse` `SystemExit` crossing the embedding boundary; a diagnostic that quotes surrounding prose | local | ephemeral |
| PV-T7-001 | FR-014, IR-003, DR-004 | T7 | unit and integration determinism | The frozen graph envelope; input permutation as an independent oracle; a before/after repository hash | `uv run pytest tests/references/test_graph.py tests/references/test_cli_graph.py tests/test_filesystem.py` | Repeated and permuted runs are byte-identical in JSON and DOT; all six edge kinds appear for resolved local relationships; unresolved and externally mapped identities produce neither nodes nor edges; an identity-invalid corpus publishes nothing; invalid targets fail as error `2` unchanged; valid publication alters only its named target | A placeholder node emitted for an unresolved reference; a partial graph published after a registry failure; an output target inside the policy scope accepted; a symlinked target followed; nondeterministic edge ordering | local | ephemeral |
| PV-T8-001 | FR-016, FR-017, DR-005 | T8 | unit and byte-idempotence | The frozen plan envelope; exhaustive enumeration over the stable finding-code set; a before/after repository hash | `uv run pytest tests/references/test_reconcile_plan.py tests/references/test_contracts.py` | Safe visible-label positives yield the exact span, replacement, and digest; destination, autolink, URL, path-like, ambiguous, editorial, and historical cases yield no entry; overlapping spans are refused; repeated preview is byte-identical and changes nothing | A planner that rewrites a URL or path span; an eligibility check that admits an unknown finding code by default; a plan entry for a `related:` advisory; overlapping edits accepted; a preview that writes a plan file | local | ephemeral |
| PV-T9-001 | FR-015, FR-018, FR-019, IR-004 | T9 | integration with fault injection | The characterized `_filesystem` writer contract; recorded pre-apply digests of every fixture target | `uv run pytest tests/references/test_reconcile_apply.py tests/test_filesystem.py tests/control_plane/test_executor.py` | A stale or unsafe plan exits nonzero with every target byte unchanged; each successful target is atomically replaced; an injected later-file failure reports applied and unapplied targets without a transaction claim; interruption leaves no truncated target; remaining blocking findings still exit `1` | An apply path that writes the first file before checking the last digest; a prior preview accepted as apply input; a claimed multi-file rollback; a partially written target left behind after interruption | local | ephemeral |
| PV-T10-001 | FR-002, FR-020, IR-006 | T10 | brownfield integration regression | The pre-change aggregate and standalone output captured in T10.0 on an overlapping metadata defect | `uv run pytest tests/references/test_aggregate.py tests/test_validate_references.py tests/control_plane tests/test_standards_graph_validators.py` | Absent or disabled configuration performs no scan and emits no reference finding; enabled configuration runs the checks; an overlapping defect keeps both contributors' distinct codes, severities, and source attribution; every legacy suite is unchanged | A contributor that runs with `enabled = false`; a standards-package selection that enables the gate; an overlap silently deduplicated; a legacy warning reclassified as an error | local | ephemeral |
| PV-T11-001 | FR-001, NFR-004, IR-001 | T11 | end-to-end across three distributions | Normalized JSON and exit status compared across source, candidate, and installed runtimes; the existing wrapper and compatibility-matrix results | Build and extract the candidate wheel per `README.md`, then `uv run pytest tests/references/test_distribution.py tests/test_installed_wrappers.py tests/package_compatibility` | `--help` exposes exactly `check`, `graph`, and `reconcile`; normalized output and exit status match across all three distributions; the commands work with no selected standard and no MCP configuration; existing wrapper and matrix suites stay green | A probe narrowed to the distribution that passes; an MCP or standards-selection import pulled onto the references path; a package-data omission that makes the installed schema unreadable; a fourth undeclared subcommand | local, plus `rexec` for the full suite | ephemeral |
| PV-T12-001 | REQ-001 | T12 | real-corpus integration and configuration transition | This repository's authored Markdown as an independent corpus; the Appendix C dogfood corpus baseline recorded before any edit; `git diff` review of every planned change | Candidate `project-standards references check --root .`, `reconcile`, reviewed `reconcile --apply`, `project-standards spec validate`, `spec lint`, the `AGENTS.md` Prettier and markdownlint gate, `git diff --check`, `uv run pytest tests/references/test_repository_corpus.py`, then `rexec -- ./scripts/verify.sh` | The declared scope is nonempty and honest; the baseline is recorded before any edit; only allowlisted edits are automated; the remediated corpus has zero blocking findings; `docs/specs/README.md` covers its declared namespaces and roots including SPEC-GSF3; the advisory inventory is structural, not count-pinned; a rerun yields an empty plan; no waiver or suppression key exists | A scope narrowed to exclude a path with real drift; a waiver key introduced to reach zero; an editorial `related:` entry added to clear an advisory; the aggregate gate enabled while blocking findings remain; a corpus test that pins a count instead of a structural property | local candidate runtime; `rexec` for the gate | ephemeral |
| PV-T13-001 | NFR-001, NFR-002, NFR-007, IR-002, DR-006 | T13 | integration and invariant regression under adversarial input | Injected wrong results proven to be detected before the real implementation runs; the specification's ERR-001–ERR-008 taxonomy; a before/after repository hash | `rexec -- uv run pytest tests/references` under network denial, including `tests/references/test_security.py` and `tests/references/test_invariants.py` | Path, encoding, and ordering inputs preserve every determinism and containment invariant; socket APIs are denied on all read paths; an invalid graph target is unchanged at exit `2`; injected failures leave no partial output; the status matrix covers ERR-001–ERR-008; diagnostics omit unrelated text; no persistent state is written; no numeric resource limit was invented | An assertion that passes against its own injected wrong result; a production fix applied inside this task instead of an appended correction task; a partial output file left after an injected failure; a diagnostic echoing surrounding prose; a persisted cache file | `rexec`, network-denied | ephemeral |
| PV-T14-001 | NFR-005, REQ-002 | T14 | documentation execution and reproducible measurement | Every documented command executed against candidate bytes; a repeated benchmark run as its own reproducibility oracle; `meta/versioning.md` | Record the Appendix C cold-run benchmark, then `uv run pytest tests/references/test_performance.py tests/references/test_documentation.py`, execute each documented example against the extracted candidate wheel, and run `rexec -- ./scripts/verify.sh --full` plus the three-distribution probes | The benchmark record states environment, corpus shape, method, and result without hardcoded counts and reproduces; every documented command and example behaves as documented; the documentation distinguishes explicit availability, aggregate opt-in, standards adoption, and MCP; the versioning classification is recorded; the full gate and probes pass | A documented example relaxed to match a defect; a benchmark stabilized by hardcoding a corpus count; documentation claiming a standards selection or MCP enables the feature; a numeric performance threshold asserted as a release gate | local candidate runtime; `rexec` for the full gate | ephemeral |

## Appendix C. Durable Evidence

Three artifacts must outlive ephemeral execution state. The `plan-authoring` bridge at version 3.5.0 rejects every Appendix C form that defines a machine-resolvable `EV-###` identifier, so these records are named and owned here and are enforced through their owning task's acceptance and §12 rather than through the parsed `evidence` field. Treat that as an engine limitation, not a licence to skip the artifact.

| Record | Producing Task | Committed Path | Contents / Provenance | Privacy Exclusions | Retention Reason and Duration |
| --- | --- | --- | --- | --- | --- |
| Dogfood corpus baseline | T12 | `docs/research/2026-07-31-durable-document-references-dogfood-baseline.md` | This repository's full-corpus blocking and advisory inventory captured before any remediation edit: repository-relative paths, stable finding codes, severities, and structural counts, with the candidate-wheel runtime version and commit in the document header. | No unrelated prose excerpts, no credential material, no host identifiers. | T12 destroys the state this record describes, so it becomes unreproducible from committed source; retain until the feature's first release is published. |
| Cold-run benchmark record | T14 | `docs/reference-tooling.md`, benchmark section | Environment description, corpus shape, method, invocation, and measured result, with toolchain versions, commit, and runner identity class. | No host identifiers; no corpus count used as a test assertion. | The measurement depends on hardware, corpus, and toolchain state at run time and is not reproducible from source; retain for the life of the documented feature. |
| Security review receipt | T13 | `docs/research/2026-07-31-durable-document-references-security-review.md` | The review completing SPEC-GSF3 §13.6: reviewer, date, commit, reviewed surfaces, each checklist item's disposition, and the accepted no-hard-resource-cap boundary. | No exploit payloads, no credential material, no host identifiers. | A review judgment is not reproducible by rerunning tests and is a release precondition; retain for the life of the released feature. |

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Additional formal-identifier namespace adapters | SPEC-GSF3 WH-001: v1 proves the policy against specifications and ADRs first. | A concrete repository requires another stable identifier family and supplies its canonical declaration and reference grammar; file a specification revision. |
| Persistent or incremental scan caching | SPEC-GSF3 WH-002: no measured need before a benchmark exists. | The Appendix C cold-run record shows a material performance problem in a supported corpus. |
| MCP resources or tools for reference reports and graphs | SPEC-GSF3 WH-003: CLI-only delivery avoids protocol, response-size, and security obligations in v1. | The CLI contracts are stable and an approved MCP use case requires remote exposure. |
| Relocation into `project-toolbox` | SPEC-GSF3 WH-004: `project-toolbox` exists at 1.1 but delivers managed checklists and a routing skill, not wheel-distributed Python subsystems. | The owner approves a migration preserving public contracts and the family gains a delivery form for wheel-distributed tooling. |
| Cross-file transactional rollback for reconciliation | SPEC-GSF3 WH-005: the executor guarantees per-file atomicity only, and v1 will not claim more than it provides. | The mutation platform gains and proves an all-or-nothing multi-file transaction contract. |
| Hypothesis property tests | D-008: no new dev dependency was approved for v1. | The owner authorizes `uv add --dev hypothesis`; the parametrized invariants become the migration baseline. |
