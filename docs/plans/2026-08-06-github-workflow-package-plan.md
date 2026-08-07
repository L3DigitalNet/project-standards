---
plan_format: 3
title: 'GitHub Workflow Standard Package Implementation Plan'
slug: 'github-workflow-package'
status: active
revision: 1
revises_revision: 0
revision_reason: 'initial plan'
pause_reason: ''
source: 'SPEC-GHW1 approved rev 1.0'
spec_ref: 'docs/specs/2026-08-06-github-workflow-package-spec.md'
created: 2026-08-06
updated: 2026-08-06
owners:
  - 'Chris Purcell / L3DigitalNet'
  - 'Coding agent under human review'
---

# GitHub Workflow Standard Package Implementation Plan

> **Definition, not state.** Authoring drafts live in `.project-pipeline/2026-08-06-github-workflow-package/authoring/`; generated execution status and evidence pointers live in `.project-pipeline/2026-08-06-github-workflow-package/execution/`.

## 1. Objective

Deliver `github-workflow` 1.0: a new Catalog 5 consumer package that packages the GitHub Repository Administration Standard's phases 1–2 for organization-owned repositories. The package ships a mandatory skill with six reference files, a compact invariant-bearing managed block, a two-option configuration, the standard offline provider set, and `gh-workflow` — a committed, reproducibly built linux/amd64 static Go binary with nine subcommands that carries the deterministic plumbing (validated mutations, ledger/summary/receipt rendering, org-schema audit, readiness check) so routine GitHub mechanics stay out of model context. Completion means the package is release-ready: every SPEC-GHW1 Must requirement is implemented with passing proof, the repository's full gate is green including the new Go lane, and the spec's traceability matrix is filled. Actual release-train publication is outside this plan (spec OQ-001, owner decision).

The dominant invariants: everything delivered is `managed` (zero create-only artifacts, bug 006 untouched), providers never touch the network, organization schema is never mutated by any packaged component, and the published payload stays organization-agnostic.

## 2. Authority and Source Map

| Source | Source Role | Authority / Use | Version / Date | Affected Plan Surface |
| --- | --- | --- | --- | --- |
| `request` | normative | owner directives this session: proceed to planning; close-out must surface OQ-001 rather than resolve it | 2026-08-06 | §§1–13, T11 |
| `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | normative | SPEC-GHW1 approved rev 1.0: FR-001–FR-024, NFR-001–NFR-005, IR-001–IR-004, DR-001–DR-003, C-001–C-006, NG-001–NG-006, milestones, OQ-001/OQ-002 | 2026-08-06 | all sections, T1–T11 |
| `repo:docs/specs/2026-08-06-github-workflow-package-design.md` | decision | approved design rev 1.6, decisions D0–D12 with rationale and reopen triggers | 2026-08-06 | §3, §5.4, T2–T8 |
| `repo:docs/specs/archive/2026-08-06-github-repo-administration-preliminary-design.md` | normative | the operating model the references must reproduce faithfully (fields, types, body/PR/review structures, invariants, baseline schema) | 2026-08-06 | T2, T3 |
| `repo:standards/agent-handoff/versions/1.9/payload.toml` | current-state evidence | payload vocabulary precedent: managed skill artifacts, harness-gated contributions, rendered policy, provider wiring | v5.15.0 | T1, T8 |
| `repo:standards/agent-handoff/versions/1.9/skills/agent-handoff/SKILL.md` | current-state evidence | skill structure and tone precedent for a packaged repo-local skill | v5.15.0 | T3 |
| `repo:standards/standard-bundle-authoring/versions/2.6/payload.toml` | normative | SBA 2.6 authoring contract exemplar for family manifests, payloads, config schemas, providers | v5.x current | T1, T8 |
| `repo:Makefile` | current-state evidence | ADR 0027 Go lane targets (`go-tools`, `go-check`) and no-package fallbacks to replace | 2026-08-06 | T4, T7 |
| `repo:go.mod` | current-state evidence | module path and pinned toolchain go1.26.5 | 2026-08-06 | T4, T7 |
| `repo:scripts/verify.sh` | operational evidence | canonical local Python gate invoked at T9/T10 | 2026-08-06 | §7, §12, T9, T10 |
| `repo:README.md` | operational evidence | candidate-wheel dogfood runtime (`PYTHONPATH=$PWD/build/wheel-runtime`) required by the validators | 2026-08-06 | §7, §12, T1, T9, T10 |
| `repo:AGENTS.md` | normative | markdown/python gate commands that must stay green | 2026-08-06 | §7, T10 |
| `repo:standards/catalog.md` | current-state evidence | catalog document the new family must join without disturbing existing entries | 2026-08-06 | T10 |
| `repo:tests/test_adopt_manifest.py` | current-state evidence | representative existing test-suite conventions the new package tests follow | 2026-08-06 | T9 |
| `repo:docs/handoff/architecture.md` | current-state evidence | bug 006 constraint; package-independence rule; component inventory to update at close-out | 2026-08-04 | §3.4, T8, T11 |

Conflict precedence: SPEC-GHW1 governs the package contract; SPEC-CP01/SPEC-BA02 and ADRs 0023/0024 govern control-plane mechanics where they overlap; the preliminary design doc governs operating-model content the references reproduce. No material conflicts identified.

## 3. Scope, Boundaries, and Constraints

### 3.1 In Scope

- The `standards/github-workflow/` family: manifest, immutable version `1.0` payload, config schema, resources, providers, capabilities, relations, catalog/graph integration.
- Skill content: `SKILL.md`, `agents/openai.yaml`, six references including the org schema and the summary/receipt/ledger layouts.
- The `gh-workflow` Go tool (first Go package in the repository): nine subcommands, offline-testable, reproducibly built, committed as a payload artifact.
- Managed block contributions to `AGENTS.md`/`CLAUDE.md`, rendered `policy.toml`, and the five providers.
- Package tests (contract, config, dogfood fixture, bug-006 guard, Go gate) and release-readiness documentation.

### 3.2 Out of Scope and Deferred

- Release-train publication and version selection (OQ-001; owner decides separately — spec §18.3).
- Everything the spec defers or excludes: Issue Forms (WH-001), phase-3+ enforcement/coordination (WH-002/WH-005), `migrate` provider (WH-003), non-linux/amd64 binaries (WH-006), scheduled ledger refresh (WH-007), personal-account support (NG-005), merge gating (NG-006).
- Applying the org schema to live GitHub (human-applied by design; NG-001).
- Adopting the package in any consumer repository, including this one.

### 3.3 Ownership and Preserved Behavior

| Boundary | Owner / Responsibility |
| --- | --- |
| Plan owns | Creation of the new family, the Go tool and its gate integration, package tests, catalog/index updates, spec traceability fill |
| Depends on | `project-standards` control plane (reconcile/providers), SBA 2.6 templates, Go toolchain go1.26.5, `gh` at runtime (sessions only, never in tests) |
| Does not own | Live GitHub state; consumer repos; rulesets; release publication; the operating-model text |
| Must preserve | All existing package families, catalog data, tests, and gates; the Makefile Go lane's no-package fallbacks must be replaced without breaking `go-check`; existing docs untouched except declared files |

### 3.4 Constraints and Authorization

- SBA 2.6 immutability: version `1.0` content is digest-pinned; every artifact carries a payload digest (C-001, NFR-002).
- Providers offline-deterministic; no network client imports (C-002, NFR-004); the Go tool is never invoked during reconcile or in any automated test that would require network.
- Payload organization-agnostic: no org login in any packaged source (NFR-001, C-003).
- All artifacts `policy = "managed"`; zero create-only entries (C-005).
- Skill executables are Go, committed per-platform, reproducibly built: `CGO_ENABLED=0`, `-trimpath`, toolchain pinned by `go.mod`; linux/amd64 only (C-006, NFR-005).
- Go tests never contact GitHub: all tool behavior proved against fixtures and a fake transport; the single live run is manual owner-witnessed evidence (spec §17.2).
- No destructive operations anywhere in this plan; all work is additive file creation plus declared documentation edits.

## 4. Current State and Target State

### 4.1 Current State

No `github-workflow` family exists. Catalog 5 has seven consumer packages plus two internal/reference families; `agent-handoff` 1.9 is the structural precedent. The repository Go lane (ADR 0027) has `go.mod`, a pinned toolchain, and a complete `make go-check` gate but zero Go source files — every Makefile target currently takes its "no packages yet" fallback. The spec and design brief are approved; `docs/GH-WORKFLOWS.md` does not exist anywhere (it is a consumer-side generated file, never part of this repository's delivery).

### 4.2 Target State

`standards/github-workflow/` validates end to end: graph, catalog, digests, agent-summary limit, and dogfood fixture reconcile producing the spec §3.2 consumer tree. `cmd/gh-workflow` + `internal/ghworkflow` are the repository's first Go packages, green under `make go-check`, with the committed binary byte-reproducible from source. The full repository gate (`scripts/verify.sh`, wheel-runtime dogfood, markdown gates, Go gate) passes. SPEC-GHW1 §17.3 shows every requirement Passing with its proving command.

### 4.3 Delta Summary

| Area | Current | Target | Must Preserve |
| --- | --- | --- | --- |
| Package families | 9 (7 consumer) | 10 (8 consumer) with `github-workflow@1.0` | Existing families byte-identical |
| Go lane | Toolchain only, no sources | First packages + committed static binary | `go-check` green; no-package fallbacks removed only by real packages |
| Catalog/graph | 9-family projections | 10-family projections, validated | Existing entries unchanged |
| Tests | No `github-workflow` coverage | Contract/config/dogfood/Go coverage per spec §17.2 | Existing suites green |
| SPEC-GHW1 §17.3 | 36 rows Not Started | All rows Passing with commands | Spec change-control (revision rows for edits) |

## 5. Change Surface and Architecture

### 5.1 Components and Ownership

| Component / Surface | Current Responsibility | Planned Responsibility | Paths / Contracts | Owning Task |
| --- | --- | --- | --- | --- |
| Family manifest + payload skeleton | none | digest-pinned family validating in graph/catalog | `standards/github-workflow/standard.toml`, `standards/github-workflow/versions/1.0/payload.toml` | T1 (skeleton), T8 (final) |
| Reference files (6) | none | operating-model reproductions + layouts | `standards/github-workflow/versions/1.0/skills/github-workflow/references/` | T2 |
| Skill + Codex companion | none | trigger boundary, refusals, routing, refresh/staleness rules | `standards/github-workflow/versions/1.0/skills/github-workflow/SKILL.md` | T3 |
| Go tool: module, plumbing, `audit` | none | gh-auth client, schema/policy loaders, audit findings engine | `cmd/gh-workflow/`, `internal/ghworkflow/` | T4 |
| Go tool: layout engine, `ledger`/`summary`/`receipt` | none | one rendering engine, three output surfaces | `internal/ghworkflow/render/` | T5 |
| Go tool: `new`/`set`/`close`/`reopen`/`check` | none | validated mutations, ordered failure-safe terminal sync, readiness findings | `internal/ghworkflow/mutate/` | T6 |
| Reproducible build + committed binary | none | byte-reproducible artifact + rebuild verification | `scripts/build-gh-workflow.sh`, `standards/github-workflow/versions/1.0/skills/github-workflow/bin/gh-workflow` | T7 |
| Providers, contributions, config, policy | none | render-semantic/validate/verify/drift-check/upgrade; blocks; `policy.toml` | `standards/github-workflow/versions/1.0/providers/` | T8 |
| Package tests + fixtures | none | spec §17.2 coverage incl. bug-006 guard | `tests/` new modules + fixtures | T9 |
| Family docs, catalog, spec traceability | none | README/adopt/agent-summary final; catalog/index; §17.3 fill; live-run evidence | family docs, `standards/catalog.md`, spec | T10 |
| Handoff/close-out | current handoff state | architecture/specs-plans/state updates, harvest | `docs/handoff/` | T11 |

### 5.2 Control / Data / State Flow

Reconcile (offline) delivers managed artifacts and renders blocks/policy from config. Agent sessions load the skill at the mutation boundary and route plumbing through `bin/gh-workflow`, which acts under the operator's `gh` authentication: repository work-state reads/writes, read-only org audit against `references/org-schema.yaml`, and whole-file atomic generation of the consumer's `docs/GH-WORKFLOWS.md`. Trust boundaries: providers never online; tool never mutates org schema; ledger content never enters payload digests (consumer-generated).

### 5.3 Change-Surface Matrix

| Surface | Applies? | Invariant / Required Change | Proof | Task |
| --- | --- | --- | --- | --- |
| Behavior | yes | nine subcommands with fixture-proved behavior | PV-T4-001, PV-T5-001, PV-T6-001 | T4–T6 |
| Architecture / dependency direction | yes | first Go packages; `cmd` → `internal` only; no Python↔Go coupling | PV-T7-001 | T4, T7 |
| Public / cross-task interface | yes | payload/config/provider contracts per SBA 2.6 | PV-T8-001 | T8 |
| Data / state | yes | `org-schema.yaml` fidelity; `policy.toml` rendering; ledger whole-file atomic write | PV-T2-001, PV-T5-001, PV-T8-001 | T2, T5, T8 |
| Configuration | yes | exactly `organization` + `harnesses`; reject unknown/empty | PV-T8-002 | T8 |
| Security / trust | yes | no credentials anywhere; org read-only; refusals present | PV-T3-001, PV-T6-001, PV-T9-001 | T3, T6, T9 |
| Compatibility / migration | yes | no legacy predecessor; existing families untouched | PV-T9-001 | T9 |
| Operations / deployment | yes | go-check integrated; reproducible-build check wired | PV-T7-001 | T7 |
| Documentation | yes | family docs, catalog, spec §17.3, handoff | PV-T10-001 | T10, T11 |
| Durable evidence | yes | manual live audit+ledger run recorded (EV-001) | PV-T10-001 | T10 |

### 5.4 Binding Decisions

| ID | Decision | Rationale | Source | Affected Task(s) |
| --- | --- | --- | --- | --- |
| D-001 | Go layout: `cmd/gh-workflow/` (main) + `internal/ghworkflow/` (packages); no other top-level Go roots | first occupant of the ADR 0027 lane; keeps the module single-rooted | design D7/D11; `repo:go.mod` | T4–T7 |
| D-002 | GitHub access via token from `gh auth token` + direct REST/GraphQL calls behind an injected transport interface | testable with a fake transport; no network in tests; resolves the OQ-002 mechanism half | spec IR-002, OQ-002 | T4 |
| D-003 | One shared layout engine renders ledger, summary, and receipt from a common findings/work-item model | FR-022 requires identical layout semantics across the three surfaces | spec FR-017/018/019/022 | T5 |
| D-004 | Binary committed at `standards/github-workflow/versions/1.0/skills/github-workflow/bin/gh-workflow`; rebuild-and-compare check runs in the Go gate, not reconcile | NFR-005 verification belongs to this repo's gate; consumers get bytes only | spec NFR-005, C-006 | T7 |
| D-005 | Subcommand CLI surface (exact flags) is fixed in T4–T6 and swept into SKILL.md at T10, closing OQ-002 | implementer-owned per spec OQ-002 | spec OQ-002 | T4–T6, T10 |

## 6. Requirements and Acceptance

Requirement IDs FR/NFR/IR/DR are SPEC-GHW1's stable IDs, used verbatim; REQ-901 is plan-local close-out work. Priorities are the spec's.

| ID | Requirement | Source | Priority | Owner Task | Task(s) | Proof(s) |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | SKILL.md decision procedures cover types, fields, bodies, PRs, lifecycle, refusals, references | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| FR-002 | Trigger boundary incl. summary trigger and read-only exemption stated | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| FR-003 | Codex companion delivered iff `codex` harness selected | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-004 | Six reference files delivered under `references/` with pinned digests | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-005 | `field-vocabulary.md` reproduces fields/values/pinning/fields-not-to-create | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T2 | T2 | PV-T2-001 |
| FR-006 | `issue-structure.md`, `pr-standard.md` (incl. PR-existence deference + silent-repo default), `review-checklist.md` reproduce their sections | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T2 | T2 | PV-T2-001 |
| FR-007 | Harness-gated managed blocks with mandate + five standing invariants + config org | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-008 | Skill routes org audit through `gh-workflow audit`; findings to a human | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| FR-009 | Refusals stated imperatively (org mutation, mode self-promotion, readiness inference, enforcement bypass) | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| FR-010 | `policy.toml` rendered with organization for the skill/tool to read | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-011 | Every artifact `managed`; zero create-only | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8, T9 | PV-T9-001 |
| FR-012 | Providers render-semantic/validate/verify/drift-check/upgrade; no scaffold/migrate; offline | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-013 | Capabilities audit/validate/drift-check; companions agent-handoff | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| FR-014 | Family README/adopt/agent-summary within size limit | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T10 | T1, T10 | PV-T1-001, PV-T10-001 |
| FR-015 | `gh-workflow` binary artifact, 0755, static, all nine subcommands | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T7 | T7 | PV-T7-001 |
| FR-016 | `audit`: schema+policy inputs, read-only live comparison, deterministic findings, fail-closed preconditions | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T4 | T4 | PV-T4-001 |
| FR-017 | `summary-format.md` defines the attention-first operator summary layout; the skill presents summaries in it | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T2 | T2, T3 | PV-T2-001, PV-T3-001 |
| FR-018 | `summary-format.md` defines the creation receipt; skill requires it after creation | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T2 | T2, T3 | PV-T2-001, PV-T3-001 |
| FR-019 | `ledger`: `docs/GH-WORKFLOWS.md` with header, TOC anchors, layout; atomic whole-file; gate-clean output | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T5 | T5 | PV-T5-001 |
| FR-020 | Skill refresh rule (after mutations + on demand) and staleness rule | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| FR-021 | `set`/`new`/`close`/`reopen`: schema-validated mutations, scaffold+receipt on create, ordered failure-safe terminal sync; org read-only | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T6 | T6 | PV-T6-001 |
| FR-022 | `summary`/`receipt` render via the ledger layout engine to stdout | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T5 | T5 | PV-T5-001 |
| FR-023 | `check`: read-only Ready preconditions with itemized findings and exit codes | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T6 | T6 | PV-T6-001 |
| FR-024 | SKILL.md maps routine actions to subcommands; judgment boundary stated | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T3 | T3 | PV-T3-001 |
| NFR-001 | Payload organization-agnostic | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8, T9 | PV-T9-001 |
| NFR-002 | Version 1.0 immutable once released; digest-pinned | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T9 | T9 | PV-T9-001 |
| NFR-003 | Block ~12 content lines; no vocabulary inline | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Should | T8 | T8 | PV-T8-001 |
| NFR-004 | Reconcile/drift/upgrade deterministic, offline | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T9 | T9 | PV-T9-001 |
| NFR-005 | Binary reproducibly buildable; independent rebuild yields committed bytes | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T7 | T7 | PV-T7-001 |
| IR-001 | Config schema exactly `organization` + `harnesses`; reject unknown/empty | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T1, T8 | PV-T1-001, PV-T8-002 |
| IR-002 | All GitHub access via operator's `gh` auth; no embedded credentials | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T4 | T4 | PV-T4-001 |
| IR-003 | markdown-block adapter, scope `block:github-workflow`, round-trips | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| IR-004 | Non-interactive CLI, nine subcommands, JSON+human modes for read-only, zero-arg defaults | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T7 | T4, T5, T6, T7 | PV-T4-001, PV-T5-001, PV-T6-001, PV-T7-001 |
| DR-001 | `org-schema.yaml` equals the design-input baseline schema | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T2 | T2 | PV-T2-001 |
| DR-002 | `policy.toml` carries org + package version only | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T8 | T8 | PV-T8-001 |
| DR-003 | Ledger is generated consumer content: excluded from digests/drift, tool-owned whole-file | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` | Must | T5 | T5 | PV-T5-001 |
| REQ-901 | Close-out: handoff documentation reconciled; deferred work and OQ-001 surfaced to the owner, not silently resolved | `request` | Must | T11 | T11 | PV-T11-001 |

## 7. Verification and Evidence Strategy

- **Authoritative commands:** `make go-check` (Go lane: format, vet, lint, race tests, build, vulncheck, mod); `PYTHONPATH=$PWD/build/wheel-runtime uv run project-standards validate`; `scripts/verify.sh` (canonical Python gate); `uv run project-standards spec validate|lint` for spec edits; the AGENTS.md markdown gate (Prettier + markdownlint over Git-tracked scope).
- **Oracles:** SPEC-GHW1 acceptance criteria; the preliminary design doc's sections for content fidelity; SBA 2.6 schemas for payload validity; `agent-handoff@1.9` payload as structural precedent; golden fixture files for tool output.
- **Negative controls:** config with unknown option / empty values must be rejected; `set` with an invalid field value must refuse and change nothing; a corrupted committed binary must fail the rebuild-compare check; a payload containing any create-only artifact must fail the bug-006 guard test; audit/ledger under a failing fake transport must exit nonzero with no partial output.
- **Test layers:** Go unit + race (findings classification, layout engine, mutation validation, atomic write); Python package-contract/snapshot (digests, artifact inventory, summary limits); configuration accept/reject; dogfood integration (fixture consumer reconcile → spec §3.2 tree); regression (bug-006 guard); docs gates.
- **External environments:** none for any automated test (fake transport only). One manual live run (`audit` + `ledger` against the real organization) is owner-witnessed evidence, recorded durably as EV-001.
- **Evidence:** repeatable local output is ephemeral; durable `EV-###` records are defined in Appendix C.
- **Late failure:** block the verification task, append a correction task, complete it, and rerun from the anchor.

## 8. Execution Summary

| Task | Title | Disposition | Work Type | Phase | Depends On | Requirement(s) | Primary Proof | Parallel / Conflict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Family scaffold validating end to end | active | configuration | P1 | None | FR-014, IR-001 | PV-T1-001 | no / none |
| T2 | Six reference files with fidelity checks | active | behavior | P1 | T1 | FR-005, FR-006, FR-017, FR-018, DR-001 | PV-T2-001 | no / none |
| T3 | SKILL.md and Codex companion | active | behavior | P2 | T2 | FR-001, FR-002, FR-008, FR-009, FR-017, FR-018, FR-020, FR-024 | PV-T3-001 | yes / none |
| T4 | Go module, gh transport, and audit subcommand | active | behavior | P2 | T2 | FR-016, IR-002, IR-004 | PV-T4-001 | yes / none |
| T5 | Layout engine and ledger, summary, receipt subcommands | active | behavior | P2 | T4 | FR-019, FR-022, DR-003, IR-004 | PV-T5-001 | no / T6 shared registry |
| T6 | Mutation and check subcommands | active | behavior | P2 | T5 | FR-021, FR-023, IR-004 | PV-T6-001 | no / T4, T5 shared registry |
| T7 | Reproducible build, committed binary, gate wiring | active | configuration | P2 | T6 | FR-015, NFR-005, IR-004 | PV-T7-001 | no / none |
| T8 | Payload completion with providers, contributions, config, policy | active | configuration | P3 | T3, T7 | FR-003, FR-004, FR-007, FR-010, FR-011, FR-012, FR-013, NFR-001, NFR-003, IR-001, IR-003, DR-002 | PV-T8-001 | no / T1 shared payload files |
| T9 | Package tests, fixtures, and guards | active | behavior | P3 | T8 | FR-011, NFR-001, NFR-002, NFR-004 | PV-T9-001 | no / none |
| T10 | Family docs, catalog, live-run evidence, spec traceability | active | documentation | P4 | T9 | FR-014 | PV-T10-001 | no / T1, T3 shared docs |
| T11 | Close-out and handoff reconciliation | active | documentation | P4 | T10 | REQ-901 | PV-T11-001 | no / none |

## 9. Implementation Tasks

### Phase P1: family foundation and reference content

#### T1: Family scaffold validating end to end

- **disposition:** active
- **outcome:** `standards/github-workflow/` exists with `standard.toml`, a version `1.0` payload skeleton, `config.schema.json`, and minimal real family docs, all passing the graph, catalog, and standards validators.
- **work_type:** configuration
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** []
- **dependency_reason:** none
- **requirements:** [FR-014, IR-001]
- **proof:** [PV-T1-001]
- **source_refs:** [repo:standards/standard-bundle-authoring/versions/2.6/payload.toml, repo:standards/agent-handoff/versions/1.9/payload.toml, repo:docs/specs/2026-08-06-github-workflow-package-spec.md]
- **consumes:** [sba-2.6-template-shapes]
- **produces:** [github-workflow-skeleton-v1]
- **preserves:** [all existing families and catalog entries byte-identical]
- **invariants:** [no placeholder text ships; every listed file parses; `availability = "consumer"`]
- **executor_discretion:** [payload skeleton internal ordering, initial resource digests]
- **files:** [`standards/github-workflow/standard.toml` (create; owner T1), `standards/github-workflow/versions/1.0/payload.toml` (create; owner T8), `standards/github-workflow/versions/1.0/config.schema.json` (create; owner T8), `standards/github-workflow/versions/1.0/README.md` (create; owner T10), `standards/github-workflow/versions/1.0/adopt.md` (create; owner T10), `standards/github-workflow/versions/1.0/agent-summary.md` (create; owner T10)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** delete the new directory; no existing file is modified
- **acceptance:** PV-T1-001 proves the graph/catalog validators and `project-standards validate` pass with the new family present, the config schema file declares exactly the two required options, and all pre-existing validator output is unchanged
- **sub-tasks:**
  - **T1.1 PRECHECK** — confirm no `standards/github-workflow/` exists; inventory SBA 2.6 template requirements.
  - **T1.2 PROVE ABSENCE** — run the validators; confirm the family is absent from graph/catalog output.
  - **T1.3 APPLY** — create manifest, payload skeleton, config schema (`organization` string required nonempty; `harnesses` enum array required nonempty), stub README/adopt/agent-summary with real minimal content.
  - **T1.4 VERIFY** — run graph/catalog validation and the wheel-runtime `project-standards validate`.
  - **T1.5 PROVE IDEMPOTENCY** — rerun validators; identical results.
  - **T1.6 Verify Task** — run PV-T1-001; commit with checkpoint trailers.

#### T2: Six reference files with fidelity checks

- **disposition:** active
- **outcome:** `references/field-vocabulary.md`, `org-schema.yaml`, `issue-structure.md`, `pr-standard.md`, `review-checklist.md`, and `summary-format.md` exist in the payload with content faithful to the operating model and the D8/D9 layouts.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T1]
- **dependency_reason:** consumes github-workflow-skeleton-v1: the payload tree receives the files
- **requirements:** [FR-005, FR-006, FR-017, FR-018, DR-001]
- **proof:** [PV-T2-001]
- **source_refs:** [repo:docs/specs/archive/2026-08-06-github-repo-administration-preliminary-design.md, repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:docs/specs/2026-08-06-github-workflow-package-design.md]
- **consumes:** [github-workflow-skeleton-v1]
- **produces:** [reference-content-v1]
- **preserves:** [operating-model semantics unaltered — reproduction, not editorial revision]
- **invariants:** [`org-schema.yaml` parses and equals the baseline schema; `pr-standard.md` states the D12 deference and silent-repo default; `review-checklist.md` states no-automation; `summary-format.md` carries both the operator summary and the creation receipt]
- **executor_discretion:** [prose transitions, heading order within files]
- **files:** [`standards/github-workflow/versions/1.0/skills/github-workflow/references/field-vocabulary.md` (create; owner T2), `standards/github-workflow/versions/1.0/skills/github-workflow/references/org-schema.yaml` (create; owner T2), `standards/github-workflow/versions/1.0/skills/github-workflow/references/issue-structure.md` (create; owner T2), `standards/github-workflow/versions/1.0/skills/github-workflow/references/pr-standard.md` (create; owner T2), `standards/github-workflow/versions/1.0/skills/github-workflow/references/review-checklist.md` (create; owner T2), `standards/github-workflow/versions/1.0/skills/github-workflow/references/summary-format.md` (create; owner T2)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** files are additive; restore last green checkpoint
- **acceptance:** PV-T2-001 proves each file's required content elements are present (scripted content checks), `org-schema.yaml` round-trips through a YAML parser equal to the baseline, and the markdown gate passes over the new files
- **sub-tasks:**
  - **T2.1 RED** — add content-fidelity checks (checked script or test) asserting the required elements per file; expected failure: files absent.
  - **T2.2 Verify RED** — run the checks; confirm failure is absence, not harness error.
  - **T2.3 GREEN** — author the six files from the operating model and spec layouts.
  - **T2.4 Verify GREEN** — fidelity checks pass; markdown gate green on the new files.
  - **T2.5 REFACTOR** — tighten wording without semantic drift; keep checks green.
  - **T2.6 Verify Task** — run PV-T2-001; commit with checkpoint trailers.

### Phase P2: skill and tool

#### T3: SKILL.md and Codex companion

- **disposition:** active
- **outcome:** the skill's decision procedures, trigger boundary (including the summary trigger and read-only exemption), refusals, subcommand routing map, refresh and staleness rules, and reference citations are complete; `agents/openai.yaml` mirrors the skill for Codex.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T2]
- **dependency_reason:** consumes reference-content-v1: the skill cites the six references by path and content
- **requirements:** [FR-001, FR-002, FR-008, FR-009, FR-017, FR-018, FR-020, FR-024]
- **proof:** [PV-T3-001]
- **source_refs:** [repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:standards/agent-handoff/versions/1.9/skills/agent-handoff/SKILL.md]
- **consumes:** [reference-content-v1]
- **produces:** [skill-content-v1]
- **preserves:** [judgment boundary — no procedure moves value selection or content authoring into tool instructions]
- **invariants:** [every refusal imperative; every routine action mapped to its subcommand; receipt required after creation; findings handed to a human]
- **executor_discretion:** [section ordering, phrasing, openai.yaml metadata shape]
- **files:** [`standards/github-workflow/versions/1.0/skills/github-workflow/SKILL.md` (create; owner T3), `standards/github-workflow/versions/1.0/skills/github-workflow/agents/openai.yaml` (create; owner T3)]
- **parallel_safe:** yes
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** additive; restore last green checkpoint
- **acceptance:** PV-T3-001 proves scripted content checks find the trigger boundary, all four refusals, the routing map covering all nine subcommands, the pre-execution platform/binary check (EC-006 — the skill checks because a foreign-platform binary cannot self-diagnose), the refresh + staleness rules, the summary-layout and creation-receipt directives (FR-017/FR-018 skill clauses), and references to all six files; markdown gate green
- **sub-tasks:**
  - **T3.1 RED** — add content checks for the required skill elements; expected failure: file absent.
  - **T3.2 Verify RED** — run checks; confirm the failure is absence.
  - **T3.3 GREEN** — author SKILL.md and openai.yaml.
  - **T3.4 Verify GREEN** — checks pass; markdown gate green.
  - **T3.5 REFACTOR** — compress prose; keep checks green.
  - **T3.6 Verify Task** — run PV-T3-001; commit with checkpoint trailers.

#### T4: Go module, gh transport, and audit subcommand

- **disposition:** active
- **outcome:** first Go packages exist (`cmd/gh-workflow`, `internal/ghworkflow`): token acquisition via `gh auth token`, an injected HTTP transport interface with a fake for tests, loaders for `org-schema.yaml`/`policy.toml`, and a working `audit` subcommand classifying match/missing/mismatch/extra with fail-closed preconditions and human+JSON output.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T2]
- **dependency_reason:** consumes reference-content-v1: loaders and audit fixtures consume the `org-schema.yaml` format T2 fixes
- **requirements:** [FR-016, IR-002, IR-004]
- **proof:** [PV-T4-001]
- **source_refs:** [repo:go.mod, repo:Makefile, repo:docs/specs/2026-08-06-github-workflow-package-spec.md]
- **consumes:** [reference-content-v1]
- **produces:** [ghworkflow-core-v1]
- **preserves:** [`make go-check` green throughout; no network in any test]
- **invariants:** [org-scoped calls read-only; missing authentication or unreachable API → nonzero exit, no partial report; no credential material in source or output]
- **executor_discretion:** [internal package decomposition, stdlib flag handling, fixture format, self-registering subcommand files so later tasks add files rather than rewriting shared registration]
- **files:** [`cmd/gh-workflow/main.go` (create; owner T4), `internal/ghworkflow/` (create; owner T4), `go.mod` (modify; owner T4), `go.sum` (modify; owner T4)]
- **parallel_safe:** yes
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** Go lane is additive; restore last green checkpoint; `go-check` re-verifies
- **acceptance:** PV-T4-001 proves fixture-driven tests cover every finding class and every precondition failure (fail-closed), zero-argument default resolution, JSON and human output, and `make go-check` passes with the new packages
- **sub-tasks:**
  - **T4.1 RED** — write failing tests for finding classification and precondition behavior against the fake transport.
  - **T4.2 Verify RED** — failures are missing implementation.
  - **T4.3 GREEN** — implement transport, loaders, findings engine, `audit`.
  - **T4.4 Verify GREEN** — targeted tests + `make go-check`.
  - **T4.5 REFACTOR** — extract the shared pieces T5/T6 will consume; keep green.
  - **T4.6 Verify Task** — run PV-T4-001; commit with checkpoint trailers; record the chosen CLI mechanism for OQ-002 in task notes.

#### T5: Layout engine and ledger, summary, receipt subcommands

- **disposition:** active
- **outcome:** one rendering engine produces the attention-first layout from a work-item model; `ledger` writes `docs/GH-WORKFLOWS.md` (header, TOC anchors, atomic whole-file replace, gate-clean output), `summary` and `receipt` print the same semantics to stdout.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T4]
- **dependency_reason:** consumes ghworkflow-core-v1: transport, models, and the subcommand registry
- **requirements:** [FR-019, FR-022, DR-003, IR-004]
- **proof:** [PV-T5-001]
- **source_refs:** [repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:docs/specs/2026-08-06-github-workflow-package-design.md]
- **consumes:** [ghworkflow-core-v1]
- **produces:** [render-engine-v1]
- **preserves:** [prior ledger bytes on any failed write (atomic temp+rename)]
- **invariants:** [whole-file ownership; generated header with timestamp+version+notice; TOC anchor for every section; output conforms unmodified to the markdown-tooling default Prettier+markdownlint gate — stricter consumer rules are consumer policy]
- **executor_discretion:** [engine internals, golden-fixture organization]
- **files:** [`internal/ghworkflow/render/` (create; owner T5), `cmd/gh-workflow/main.go` (modify; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T6]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore last green checkpoint; atomic write invariant prevents partial consumer files
- **acceptance:** PV-T5-001 proves golden-fixture equality for all three surfaces, TOC/header presence, zero-argument and JSON/human modes, atomicity under injected write failure (prior bytes intact), and that generated output passes the markdown-tooling default Prettier and markdownlint configuration (this repository's gate)
- **sub-tasks:**
  - **T5.1 RED** — golden-fixture and atomicity tests failing for the absent engine.
  - **T5.2 Verify RED** — confirm failure cause.
  - **T5.3 GREEN** — implement engine and three subcommands.
  - **T5.4 Verify GREEN** — targeted tests; run Prettier/markdownlint against generated fixture output.
  - **T5.5 REFACTOR** — deduplicate against audit output paths; keep green.
  - **T5.6 Verify Task** — run PV-T5-001; `make go-check`; commit with checkpoint trailers.

#### T6: Mutation and check subcommands

- **disposition:** active
- **outcome:** validated mutation subcommands and the read-only readiness check: `set` refuses invalid values listing the valid set; `new` scaffolds the canonical body, applies initial fields, and prints the receipt; `close`/`reopen` apply `Workflow` terminals and close reasons as an ordered failure-safe sequence per FR-021; `check` itemizes Ready-precondition findings with exit codes.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T5]
- **dependency_reason:** consumes render-engine-v1 for the receipt-on-create path; serializes shared registry ownership after T5
- **requirements:** [FR-021, FR-023, IR-004]
- **proof:** [PV-T6-001]
- **source_refs:** [repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:docs/specs/2026-08-06-github-workflow-package-design.md]
- **consumes:** [render-engine-v1, ghworkflow-core-v1]
- **produces:** [ghworkflow-mutations-v1]
- **preserves:** [organization schema untouched by every code path — no org-mutation API surface exists in the client]
- **invariants:** [validation precedes any mutating call; refusal changes nothing remotely; terminal pairing is an ordered failure-safe sequence — divergent state reported exactly, corrective retry required before success (FR-021)]
- **executor_discretion:** [flag naming within IR-004 constraints, error text]
- **files:** [`internal/ghworkflow/mutate/` (create; owner T6), `cmd/gh-workflow/main.go` (modify; owner T4)]
- **parallel_safe:** no
- **conflicts_with:** [T4, T5]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** restore last green checkpoint; fake-transport tests cannot leave remote state
- **acceptance:** PV-T6-001 proves via fake transport: invalid-value refusal with zero mutating calls (EC-008), scaffold + receipt on create, the ordered terminal pairing including the divergent-state report and corrective-retry path, reopen restoration, every `check` precondition class, and IR-004 zero-argument plus JSON/human output for `check`; `make go-check` green
- **sub-tasks:**
  - **T6.1 RED** — failing tests per subcommand behavior incl. refusal and partial-failure paths.
  - **T6.2 Verify RED** — confirm failure cause.
  - **T6.3 GREEN** — implement the five subcommands.
  - **T6.4 Verify GREEN** — targeted tests.
  - **T6.5 REFACTOR** — consolidate validation paths; keep green.
  - **T6.6 Verify Task** — run PV-T6-001; `make go-check`; commit with checkpoint trailers.

#### T7: Reproducible build, committed binary, gate wiring

- **disposition:** active
- **outcome:** a deterministic build path (`CGO_ENABLED=0`, `-trimpath`, pinned toolchain) produces `bin/gh-workflow`; the binary is committed into the payload tree at mode 0755; a rebuild-and-byte-compare check is wired into the Go gate; the full nine-subcommand CLI surface is frozen.
- **work_type:** configuration
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T6]
- **dependency_reason:** consumes ghworkflow-mutations-v1: the committed binary must contain all subcommands
- **requirements:** [FR-015, NFR-005, IR-004]
- **proof:** [PV-T7-001]
- **source_refs:** [repo:Makefile, repo:go.mod, repo:docs/specs/2026-08-06-github-workflow-package-spec.md]
- **consumes:** [ghworkflow-mutations-v1, render-engine-v1, ghworkflow-core-v1]
- **produces:** [gh-workflow-binary-v1]
- **preserves:** [existing Makefile targets; `go-check` extended, not altered]
- **invariants:** [one exact build invocation: `GOOS=linux GOARCH=amd64 GOAMD64=v1 CGO_ENABLED=0 go build -trimpath -buildvcs=false` with deterministic linker flags; rebuild from a clean worktree at the same commit yields byte-identical output; binary statically linked; payload declares `mode = "0755"` (the delivered mode is proved by T9's fixture reconcile)]
- **executor_discretion:** [make target vs script internals only — the build invocation itself is fixed by NFR-005, including `-ldflags` and operands]
- **files:** [`Makefile` (modify; owner T7), `scripts/build-gh-workflow.sh` (create; owner T7), `standards/github-workflow/versions/1.0/skills/github-workflow/bin/gh-workflow` (create; owner T7)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** rebuild regenerates the artifact; restore last green checkpoint
- **acceptance:** PV-T7-001 proves two independent clean-worktree same-commit builds byte-match the committed binary using the exact prescribed invocation, the gate check fails on a deliberately corrupted binary (negative control), and `--help` enumerates all nine subcommands
- **sub-tasks:**
  - **T7.1 PRECHECK** — verify toolchain pin and clean tree.
  - **T7.2 PROVE ABSENCE** — rebuild-compare check fails before the binary exists.
  - **T7.3 APPLY** — add build target, build, commit binary, wire the compare check into `go-check`.
  - **T7.4 VERIFY** — double-build byte comparison; corrupted-binary negative control.
  - **T7.5 PROVE IDEMPOTENCY** — repeat build → identical bytes.
  - **T7.6 Verify Task** — run PV-T7-001; commit with checkpoint trailers.

### Phase P3: package integration

#### T8: Payload completion with providers, contributions, config, policy

- **disposition:** active
- **outcome:** `payload.toml` is complete and digest-pinned over every artifact including the binary; providers render-semantic/validate/verify/drift-check/upgrade implemented; harness-gated block contributions carry the mandate + five standing invariants with config-rendered organization; `policy.toml` renders org + package version; capabilities and companions declared.
- **work_type:** configuration
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T3, T7]
- **dependency_reason:** consumes skill-content-v1 and gh-workflow-binary-v1: digests require final bytes of skill content and binary
- **requirements:** [FR-003, FR-004, FR-007, FR-010, FR-011, FR-012, FR-013, NFR-001, NFR-003, IR-001, IR-003, DR-002]
- **proof:** [PV-T8-001, PV-T8-002]
- **source_refs:** [repo:standards/agent-handoff/versions/1.9/payload.toml, repo:standards/standard-bundle-authoring/versions/2.6/payload.toml, repo:docs/specs/2026-08-06-github-workflow-package-spec.md]
- **consumes:** [skill-content-v1, gh-workflow-binary-v1]
- **produces:** [payload-1.0-final]
- **preserves:** [organization-agnostic payload sources; existing families untouched]
- **invariants:** [zero create-only entries; every artifact `managed` and digested; block body ≈12 content lines; providers import no network client]
- **executor_discretion:** [provider module structure, resource id naming]
- **files:** [`standards/github-workflow/versions/1.0/payload.toml` (modify; owner T8), `standards/github-workflow/versions/1.0/config.schema.json` (modify; owner T8), `standards/github-workflow/versions/1.0/providers/gh_workflow.py` (create; owner T8), `standards/github-workflow/versions/1.0/resources/policy.toml` (create; owner T8)]
- **parallel_safe:** no
- **conflicts_with:** [T1]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** payload edits are additive to the new family; restore last green checkpoint
- **acceptance:** PV-T8-001 proves graph/catalog/standards validation over the complete payload, block render for each harness combination with the required invariants present, policy rendering, and provider validate/verify/drift-check coverage of all artifacts; PV-T8-002 proves config acceptance of valid input and rejection of unknown options, missing options, and empty values
- **sub-tasks:**
  - **T8.1 PRECHECK** — inventory all artifact bytes final; digests computable.
  - **T8.2 PROVE ABSENCE** — validation fails on the incomplete payload (missing artifacts/providers).
  - **T8.3 APPLY** — complete payload entries, providers, contributions, policy template, config schema.
  - **T8.4 VERIFY** — full standards validation; render matrix (claude-code only, codex only, both).
  - **T8.5 PROVE IDEMPOTENCY** — re-render → identical outputs.
  - **T8.6 Verify Task** — run PV-T8-001 and PV-T8-002; commit with checkpoint trailers.

#### T9: Package tests, fixtures, and guards

- **disposition:** active
- **outcome:** repository test coverage per spec §17.2: contract/digest/inventory tests, config accept/reject, dogfood fixture consumer reconciling to the spec §3.2 tree per harness selection (EC-005), bug-006 guard (zero create-only), org-agnostic payload scan, immutability wiring, offline determinism.
- **work_type:** behavior
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T8]
- **dependency_reason:** consumes payload-1.0-final: tests assert the final payload contract
- **requirements:** [FR-011, NFR-001, NFR-002, NFR-004]
- **proof:** [PV-T9-001]
- **source_refs:** [repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:scripts/verify.sh]
- **consumes:** [payload-1.0-final]
- **produces:** [test-coverage-v1]
- **preserves:** [existing suites green; no network in any test]
- **invariants:** [negative controls actually fail on seeded defects (create-only entry, org literal, digest mismatch)]
- **executor_discretion:** [test module organization, fixture minimization]
- **files:** [`tests/test_github_workflow_package.py` (create; owner T9), `tests/test_github_workflow_dogfood.py` (create; owner T9), `tests/fixtures/github_workflow/` (create; owner T9)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** tests are additive; restore last green checkpoint
- **acceptance:** PV-T9-001 proves the new suites pass, each negative control fails when its defect is seeded, and `scripts/verify.sh` passes end to end with the new family
- **sub-tasks:**
  - **T9.1 RED** — write the suites; confirm the seeded-defect negative controls fail correctly.
  - **T9.2 Verify RED** — failure causes are the seeded defects.
  - **T9.3 GREEN** — unseed; suites pass against the real payload.
  - **T9.4 Verify GREEN** — `scripts/verify.sh` full pass.
  - **T9.5 REFACTOR** — deduplicate fixture plumbing; keep green.
  - **T9.6 Verify Task** — run PV-T9-001; commit with checkpoint trailers.

### Phase P4: release readiness and close-out

#### T10: Family docs, catalog, live-run evidence, spec traceability

- **disposition:** active
- **outcome:** final README/adopt/agent-summary (within the byte limit); `standards/catalog.md` and index/graph data updated; the CLI surface swept into SKILL.md closing OQ-002; one owner-witnessed live `audit` + `ledger` run against the real organization recorded as EV-001; SPEC-GHW1 §17.3 filled to Passing and OQ-002 marked Answered with a spec revision row.
- **work_type:** documentation
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T9]
- **dependency_reason:** consumes test-coverage-v1: documentation and traceability describe the verified final state
- **requirements:** [FR-014]
- **proof:** [PV-T10-001]
- **source_refs:** [repo:standards/catalog.md, repo:docs/specs/2026-08-06-github-workflow-package-spec.md, repo:AGENTS.md, repo:README.md]
- **consumes:** [test-coverage-v1]
- **produces:** [docs-readiness-v1]
- **preserves:** [spec change-control: content edits carry a revision row; other catalog entries unchanged]
- **invariants:** [agent-summary within the enforced limit; live run is read-only plus a ledger write in a scratch consumer checkout, never this repository]
- **executor_discretion:** [doc prose, evidence record format]
- **files:** [`standards/github-workflow/versions/1.0/README.md` (modify; owner T10), `standards/github-workflow/versions/1.0/adopt.md` (modify; owner T10), `standards/github-workflow/versions/1.0/agent-summary.md` (modify; owner T10), `standards/catalog.md` (modify; owner T10), `docs/specs/2026-08-06-github-workflow-package-spec.md` (modify; owner T10), `standards/github-workflow/versions/1.0/skills/github-workflow/SKILL.md` (modify; owner T3), `docs/research/2026-08-06-github-workflow-live-run-evidence.md` (create; owner T10)]
- **parallel_safe:** no
- **conflicts_with:** [T1, T3]
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [EV-001]
- **recovery:** documentation edits; restore last green checkpoint
- **acceptance:** PV-T10-001 proves the full gate battery green (verify.sh, wheel dogfood validate, go-check, markdown gate, spec validate/lint), §17.3 rows all Passing with real commands, and EV-001 exists with the live-run record
- **sub-tasks:**
  - **T10.1 INVENTORY** — enumerate the documentation surfaces (family docs, catalog, SKILL.md CLI sweep, spec §17.3/§21, EV-001 target); confirm prior tasks terminal and gates green.
  - **T10.2 UPDATE** — finalize docs, catalog, CLI-surface sweep, and spec updates with a revision row; run the witnessed live `audit` + `ledger` in a scratch consumer checkout and record EV-001.
  - **T10.3 VERIFY REFERENCES** — full gate battery (verify.sh, wheel validate, go-check, markdown gate, spec validate/lint); §17.3 all Passing; links and IDs resolve.
  - **T10.4 Verify Task** — run PV-T10-001; commit with checkpoint trailers.

#### T11: Close-out and handoff reconciliation

- **disposition:** active
- **outcome:** `docs/handoff/architecture.md`, `specs-plans.md`, and state reflect the delivered package; deferred work (WH items, OQ-001 release placement) is visible to the owner; plan close-out harvested; scratch torn down per policy.
- **work_type:** documentation
- **checkpoint:** one green commit with the required `Plan-*` checkpoint trailers
- **boundary:** cross-task
- **depends_on:** [T10]
- **dependency_reason:** consumes docs-readiness-v1: close-out records final verified state
- **requirements:** [REQ-901]
- **proof:** [PV-T11-001]
- **source_refs:** [request, repo:docs/handoff/architecture.md]
- **consumes:** [docs-readiness-v1]
- **produces:** [close-out-record-v1]
- **preserves:** [handoff document shape rules (160-char bullets); agent-handoff validate/drift-check green]
- **invariants:** [no irreplaceable evidence deleted; OQ-001 explicitly surfaced to the owner, not silently resolved]
- **executor_discretion:** [handoff wording]
- **files:** [`docs/handoff/architecture.md` (modify; owner T11), `docs/handoff/specs-plans.md` (modify; owner T11), `docs/handoff/state.md` (modify; owner T11), `docs/plans/2026-08-06-github-workflow-package-plan.md` (modify; owner T11)]
- **parallel_safe:** no
- **conflicts_with:** []
- **supersedes:** []
- **superseded_by:** []
- **evidence:** [ephemeral]
- **recovery:** documentation only; restore last green checkpoint
- **acceptance:** PV-T11-001 proves `project-standards agent-handoff validate --repo .` and `drift-check --repo .` pass and the close-out section is complete with OQ-001 surfaced
- **sub-tasks:**
  - **T11.1 INVENTORY** — enumerate handoff documents needing reconciliation; validators green at start.
  - **T11.2 UPDATE** — update architecture/specs-plans/state and the plan close-out; surface OQ-001 and the WH deferrals to the owner.
  - **T11.3 VERIFY REFERENCES** — `project-standards agent-handoff validate --repo .` and `drift-check --repo .`; all pointers resolve.
  - **T11.4 Verify Task** — run PV-T11-001; commit with checkpoint trailers.

## 10. Integration, Migration, and Recovery

### 10.1 Integration Sequence

1. P1 lands the family and reference content behind the standards validators.
2. P2 lands the skill and the Go lane in parallel tracks that join at T7's committed binary.
3. P3 completes and proves the payload contract (T8 → T9); `scripts/verify.sh` is the gate.
4. P4 finalizes documentation, evidence, and traceability; release publication remains outside the plan (OQ-001).

### 10.2 Migration / State / Configuration Transition

- Required: no — new family, no legacy predecessor (WH-003), no consumer migration.
- Compatibility period: not applicable; nothing existing changes behavior.
- Idempotency: validators, renders, and builds are deterministic; re-runs converge.
- Point of no return: none inside the plan; immutability begins at release publication, which is out of scope.
- Rollback / forward repair: every task is additive to a new directory tree or declared doc files; restore the last green checkpoint.
- Recovery proof: per-task recovery lines; PV-T7-001 covers artifact regeneration.

### 10.3 Late Failure and Correction

A failure discovered in T9/T10 verification blocks that task, appends a correction task with `corrects:` and `discovered_from:`, and reruns from the anchor after the correction lands. Completed tasks are never reopened; the committed binary is regenerated (not patched) whenever any Go source correction lands, through T7's build path in the correction task.

## 11. Risks, Assumptions, and Open Questions

### 11.1 Risks

| ID | Risk | Likelihood | Impact | Treatment | Owner / Task |
| --- | --- | --- | --- | --- | --- |
| R-001 | Go binary not byte-reproducible across environments (toolchain/telemetry variance) | medium | high | pin via `go.mod` toolchain and the exact invocation (`GOOS/GOARCH/GOAMD64`, `CGO_ENABLED=0`, `-trimpath`, `-buildvcs=false`, deterministic ldflags); prove with clean-worktree double-build in PV-T7-001; if variance persists, record the exact build environment in the payload and gate on it | executor / T7 |
| R-002 | Issue Fields GA API surface differs from the design doc's description | medium | medium | D-002 isolates API calls behind the transport; T4 verifies against current API docs before freezing; spec A-001 already scopes the blast radius to a references note | executor / T4 |
| R-003 | Ledger output fighting consumer markdown gates (Prettier normalization drift) | low | medium | PV-T5-001 runs the repository's actual Prettier and markdownlint over generated fixtures; render emits pre-normalized output | executor / T5 |
| R-004 | Binary bloats repository/payload beyond comfort | low | low | accepted per design D7 residual risk; stdlib-only keeps the static binary small; reopen trigger recorded in the brief | owner / T7 |

### 11.2 Assumptions

| ID | Assumption | Impact if False |
| --- | --- | --- |
| A-001 | The control plane supports binary (non-text) managed artifacts with mode preservation without platform changes | a small platform extension becomes a discovered task appended to this plan; SPEC-CP01 owners decide |
| A-002 | Stdlib-only Go suffices: HTTP and JSON are stdlib, and `org-schema.yaml` is parsed by an owned bounded-subset parser (exactly two top-level keys, string scalars and string lists, per-field maps with `type` and `values`; anything else fails closed with a parse error) — Go's stdlib has no general YAML decoder and none is needed for this owned file | if the bounded parser proves insufficient, adding a dependency is executor discretion under `go-mod-check`; digest and vulncheck gates still apply |

### 11.3 Open Questions

None.

## 12. Final Verification

- Every Must/Should requirement in §6 maps to completed tasks and passing Appendix B proof.
- `scripts/verify.sh`, `PYTHONPATH=$PWD/build/wheel-runtime uv run project-standards validate`, `make go-check`, the AGENTS.md markdown gate, and `spec validate`/`spec lint` all pass at T10.
- Dogfood fixture reconcile reproduces the spec §3.2 tree for each harness combination.
- SPEC-GHW1 §17.3 rows all Passing; OQ-002 Answered; EV-001 recorded.
- No blocker, unapproved deviation, or unresolved correction remains.

## 13. Close-out

- **Completed:** pending.
- **Decisions / deviations harvested:** pending.
- **Risks closed / accepted:** pending.
- **Deferred/discovered work filed:** pending (must include OQ-001 surfacing and the spec WH items).
- **Source/ADR/handoff reconciliation:** pending.
- **Scratch teardown:** only after no irreplaceable evidence remains.

## Appendix A. Interface and State Contracts

| Contract | Owner / Producer Task | Consumer(s) | Current | Planned / States | Errors / Limits | Compatibility / Invariant | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| github-workflow-skeleton-v1 | T1 | T2 | none | manifest + payload tree + config schema | validators reject malformed | SBA 2.6 shapes | `repo:standards/standard-bundle-authoring/versions/2.6/payload.toml` |
| reference-content-v1 | T2 | T3, T4 | none | six files; `org-schema.yaml` is the audit oracle and loader fixture format | fidelity checks | reproduction, not revision | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| skill-content-v1 | T3 | T8 | none | SKILL.md + openai.yaml final bytes | content checks | judgment boundary preserved | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| ghworkflow-core-v1 | T4 | T5, T6, T7 | none | transport interface, loaders, findings model, subcommand registry | fail-closed preconditions | org calls read-only; fake-transport testability | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| render-engine-v1 | T5 | T6, T7 | none | one engine, three surfaces; atomic ledger write | prior bytes preserved on failure | gate-clean output | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| ghworkflow-mutations-v1 | T6 | T7 | none | five subcommands; validation before mutation | refusal mutates nothing | terminal pairing ordered and failure-safe: native state first, then `Workflow` field; rerun is the corrective retry | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| gh-workflow-binary-v1 | T7 | T8 | none | committed static linux/amd64 binary, 0755 | rebuild-compare gate | byte-reproducible | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| payload-1.0-final | T8 | T9 | skeleton | complete digest-pinned payload, providers, contributions | standards validators | all-managed; org-agnostic | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| test-coverage-v1 | T9 | T10 | none | passing suites incl. negative controls and dogfood fixture | seeded defects must fail | offline; deterministic | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| docs-readiness-v1 | T10 | T11 | none | docs/catalog/spec-traceability complete; EV-001 recorded | gate battery | spec change-control respected | `repo:docs/specs/2026-08-06-github-workflow-package-spec.md` |
| close-out-record-v1 | T11 | none | none | handoff and plan close-out complete | handoff validators | OQ-001 surfaced, not resolved | `request` |

## Appendix B. Requirement-to-Proof Traceability

| Proof ID | Requirement(s) | Task | Method | Oracle | Command / Procedure | Expected Result | Negative Control | Environment | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PV-T1-001 | FR-014, IR-001 | T1 | integration | SBA 2.6 schemas + existing validator suite | `PYTHONPATH=$PWD/build/wheel-runtime uv run project-standards validate` plus graph/catalog checks | new family validates; two-option config schema present; prior output unchanged | malformed manifest variant rejected during authoring | local | ephemeral |
| PV-T2-001 | FR-005, FR-006, FR-017, FR-018, DR-001 | T2 | documentation | preliminary design doc sections; spec layout definitions | scripted fidelity checks + YAML round-trip + markdown gate on new files | all required elements present; schema equals baseline | check fails when a required element is removed | local | ephemeral |
| PV-T3-001 | FR-001, FR-002, FR-008, FR-009, FR-017, FR-018, FR-020, FR-024 | T3 | documentation | spec FR acceptance text | scripted content checks + markdown gate | boundary, refusals, routing map (9 subcommands), platform check, summary/receipt directives, refresh/staleness present | check fails on a removed refusal | local | ephemeral |
| PV-T4-001 | FR-016, IR-002, IR-004 | T4 | unit | spec finding classes; fake transport | `make go-check` plus targeted `go test ./internal/ghworkflow/...` | all finding classes and precondition failures covered; zero-argument default and JSON+human modes for `audit`; no credentials; fail-closed | failing fake transport yields nonzero exit and no partial report | local, offline | ephemeral |
| PV-T5-001 | FR-019, FR-022, DR-003, IR-004 | T5 | unit | `summary-format.md` layouts; repo Prettier/markdownlint | targeted go tests + gate run over generated fixtures | byte-equal renders; TOC/header present; zero-argument defaults and JSON+human modes for `summary`/`receipt`; atomic write preserves prior bytes on failure | injected write failure leaves original intact | local, offline | ephemeral |
| PV-T6-001 | FR-021, FR-023, IR-004 | T6 | unit | spec FR-021/023 acceptance; org-schema fixture | targeted go tests + `make go-check` | refusal with zero mutating calls; scaffold+receipt; ordered terminal pairing incl. divergence report; check classes with zero-argument default and JSON+human modes | invalid value mutates nothing; partial failure reported explicitly | local, offline | ephemeral |
| PV-T7-001 | FR-015, NFR-005, IR-004 | T7 | build | committed bytes as oracle | double clean build + byte compare wired into `make go-check`; `bin/gh-workflow --help` | byte-identical clean-worktree rebuilds via the exact prescribed invocation; nine subcommands listed | corrupted binary fails the gate check | local | ephemeral |
| PV-T8-001 | FR-003, FR-004, FR-007, FR-010, FR-012, FR-013, NFR-003, IR-003, DR-002 | T8 | integration | SBA schemas; agent-handoff precedent; spec block content | standards validation + render for each harness combination | complete digest-pinned payload; correct gating; block invariants present; ≈12-line body | render with missing config option rejected | local | ephemeral |
| PV-T8-002 | IR-001 | T8 | configuration | `config.schema.json` | schema validation acceptance and rejection cases | valid accepted; unknown/missing/empty rejected | unknown-option fixture rejected | local | ephemeral |
| PV-T9-001 | FR-011, NFR-001, NFR-002, NFR-004 | T9 | integration | payload contract; spec §3.2 tree | new pytest suites + `scripts/verify.sh` | suites pass; fixture consumer matches target tree per harness (EC-005) incl. delivered binary mode 0755 | seeded create-only entry, org literal, and digest mismatch each fail their guard | local, offline | ephemeral |
| PV-T10-001 | FR-014 | T10 | acceptance | all repository gates; live organization | verify.sh + wheel validate + go-check + markdown gate + spec validate/lint; witnessed live `audit` + `ledger` run | all green; §17.3 Passing; EV-001 recorded | gate battery fails on any seeded regression during authoring | local plus one witnessed live run | EV-001 |
| PV-T11-001 | REQ-901 | T11 | inspection | agent-handoff validators | `project-standards agent-handoff validate --repo .` and `drift-check --repo .` | both pass; close-out complete; OQ-001 surfaced | validator fails on a malformed handoff edit | local | ephemeral |

## Appendix C. Durable Evidence

| Evidence ID | Producing Task | Path | Contents / Provenance | Privacy Exclusions | Retention Reason |
| --- | --- | --- | --- | --- | --- |
| EV-001 | T10 | `docs/research/2026-08-06-github-workflow-live-run-evidence.md` | owner-witnessed live run of `gh-workflow audit` and `gh-workflow ledger` from a scratch consumer checkout: command lines, exit codes, findings summary, generated ledger header | organization name is public; no tokens or credential material recorded | live-run behavior is not reproducible offline; permanent |

## Appendix D. Deferred Work

| Item | Reason Deferred | Follow-up / Reopen Trigger |
| --- | --- | --- |
| Release-train publication of `github-workflow@1.0` | OQ-001: owner decision, post-v5.17.0 | owner schedules the train; repository release contract governs |
| Issue Forms, phase-3 enforcement, `migrate` provider, extra platforms, scheduled ledger refresh | spec WH-001–WH-007 | triggers recorded in SPEC-GHW1 §2.3 |
| Consumer adoption (including this repository) | separate operational decision per repo | owner selects the package in a consumer's `.standards/config.toml` |
