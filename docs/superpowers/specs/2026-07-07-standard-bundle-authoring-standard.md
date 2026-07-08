---
spec_id: SPEC-BA01
title: 'Standard Bundle Authoring Standard'
status: draft # draft | review | approved | superseded
profile: light # this is the Light template; see header note for sibling profiles
owner: 'Chris Purcell / L3DigitalNet'
implementer: 'Coding agent under human review'
created: '2026-07-07'
last_reviewed: '2026-07-07'
supersedes: null # SPEC id this replaces, if any
superseded_by: null # filled in when this spec is retired
related:
  adrs:
    - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
    - 'docs/adr/adr-0002-manifest-first-standard-discovery.md'
    - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
    - 'docs/adr/adr-0004-authority-map-and-conflict-free-composition.md'
    - 'docs/adr/adr-0006-standard-provider-plugin-model.md'
    - 'docs/adr/adr-0008-consumer-config-namespace-registry.md'
    - 'docs/adr/adr-0009-agent-summary-and-canonical-standard-split.md'
    - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
    - 'docs/adr/adr-0013-independent-standard-packages-and-relationship-taxonomy.md'
  tickets: []
  repositories:
    - 'L3DigitalNet/project-standards'
  prior_specs:
    - 'SPEC-MT01'
---

# `Standard Bundle Authoring Standard` — Specification (Light)

---

## Revision History

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 0.1 | 2026-07-07 | Chris Purcell / L3DigitalNet | Initial draft |
| 0.2 | 2026-07-07 | Chris Purcell / L3DigitalNet | Codex spec-review r1: dotted/nested namespace model; added manifest-safety, adopt.toml-linkage, and manual-conformance-checklist FRs; standards-index anatomy DoD; OQ-001/002 resolved |
| 0.3 | 2026-07-07 | Chris Purcell / L3DigitalNet | Codex spec-review r2: FR-012 resource/template paths made bundle-relative and contained (adr-0010), provider entrypoint clarified vs filesystem paths — last non-blocking finding; converged |

**Spec lifecycle:** This document is **living until `approved`**, then **change-controlled**: post-approval edits require a new revision row and, for scope-affecting changes, re-approval by the owner. Implementation deviations are recorded in the [Deviations Log](#deviations-log), not silently patched into requirements. When replaced, set `status: superseded` and `superseded_by:` in the frontmatter.

---

## 1. Purpose & Background

The `project-standards` repository defines standards as bundles under `standards/{id}/`, but no contract says what a standard bundle must declare. The seven current bundles are inconsistent: five have machine bundles and `registry.json` entries, `project-spec` is enforced through its CLI with no copy-adopt bundle or registry entry, and `python-coding` is an unregistered draft (see the SPEC-MT01 Step 00 baseline inventory). As the number of standards grows and the meta-repo work (`SPEC-MT01`) makes the repository mechanically self-describing — so a future standards graph, and eventually an MCP server, can discover and compose standards without hardcoding each one — that inconsistency has to be closed by a single, machine-checkable authoring contract.

This standard, the **Standard Bundle Authoring Standard**, is that contract: the "standard for standards." It defines the required anatomy of a standard bundle, the `standard.toml` manifest each bundle carries, and the authority, relationship, resource, provider, and config-namespace rules that let arbitrary standards compose without conflict. It is the `SPEC-MT01` Step 02 deliverable and realizes the Standard Bundle Authoring Contract decision ([adr-0001](../../adr/adr-0001-standard-bundle-authoring-contract.md)).

It is an **internal / reference** standard: it governs how this repository authors its own standards. It is deliberately not consumer-adopted — no `adopt.md`, no copy-adopt bundle, and no `registry.json` contract version — because no downstream repository authors its own standards today. It still ships its own `standard.toml` so the repository dogfoods the contract it defines, and adoptability can be added later without reworking the contract.

The first-release scope is the **written contract plus one worked example** (this standard's own `standard.toml`). The machine schema, typed model, fixtures, and graph-validation gate that enforce the contract are deferred to `SPEC-MT01` Steps 03–04: the contract must be settled in prose before it is mechanized. The long-term asset is a repository where adding a standard is a data/documentation change rather than a tool-code change.

---

## 2. Scope

### 2.1 In Scope

- The required and optional anatomy of a standard bundle (files, `standard.toml`, `adopt.toml` linkage, agent summaries, resources).
- The `standard.toml` manifest contract: identity, lifecycle/status, versions, config namespace, resources, capabilities, authorities, relationships, providers, and adoption mode — shown by an annotated example.
- An `adoption`-mode vocabulary that describes every current standard honestly, so today's outliers become first-class rather than exceptions.
- Authority-tuple declarations and the conflict rule for safe composition.
- The relationship taxonomy and the independent-package default.
- Config-namespace ownership rules and the lifecycle states a standard moves through, plus the ADR-backed exception process.
- This standard's own `standard.toml` (the first worked example) and a blank `standard.toml` template.

### 2.2 Out of Scope (Non-Goals — never)

| ID | Non-Goal | Reason |
| --- | --- | --- |
| NG-001 | Ship an `adopt.md` / copy-adopt bundle or a `registry.json` contract version for this standard | Internal/reference by decision; no downstream repo authors standards, so adoption machinery would serve a non-existent use case. |
| NG-002 | Modify or replace `adopt.toml` semantics | `adopt.toml` remains the artifact plane, referenced from `standard.toml` ([adr-0003](../../adr/adr-0003-separate-standard-and-artifact-manifests.md)). |

### 2.3 Won't Have in v1 (deferred — not never)

| ID | Deferred Capability | Why Deferred | Revisit When |
| --- | --- | --- | --- |
| WH-001 | The machine `standard.toml` JSON-schema, Pydantic model, and fixtures | Those are `SPEC-MT01` Step 03; the contract must be settled first | Step 03 begins |
| WH-002 | The standards-graph validator and its verification-gate wiring | `SPEC-MT01` Step 04; needs the schema/model from Step 03 | Step 04 begins |
| WH-003 | Writing `standard.toml` for the seven existing standards (the retrofit) | `SPEC-MT01` Step 05; this spec defines the contract they are written to | Step 05 begins |
| WH-004 | Consumer adoptability (adopt guide, external-author templates, a contract version) | No external standard-author consumer exists yet | A downstream repository needs to author its own standards |

### 2.4 Boundaries

| Boundary | Description |
| --- | --- |
| System owns | The written bundle-authoring contract (`standards/standard-bundle-authoring/README.md`), this standard's own `standard.toml`, and a blank `standard.toml` template. |
| System depends on | `SPEC-MT01` and its accepted ADRs (adr-0001…0013); the existing bundle anatomy, `adopt.toml` model, and `registry.json`; and the Markdown Frontmatter, Markdown Tooling, and Project Specification standards that govern this document. |
| System does not own | The `standard.toml` schema / model / validator (Steps 03–04), the retrofit of existing standards (Step 05), the standards graph, or any MCP runtime. |

---

> **Sections §3–§6 are Standard/Full-tier** (Context, Goals, Stakeholders, Glossary) and are intentionally omitted at the Light profile.

## 7. Requirements

### 7.1 Functional Requirements

| ID | Requirement | Rationale | Acceptance Criteria | Priority |
| --- | --- | --- | --- | --- |
| FR-001 | The standard shall define the required and optional anatomy of a standard bundle. | New standards need a uniform, discoverable structure. | The README lists which files MUST vs SHOULD exist, including the `standard.toml` requirement and the explicit non-adoptable marker for CLI/reference-only standards. | Must |
| FR-002 | The standard shall specify the `standard.toml` manifest contract, each field marked required or optional and shown in one annotated example. | Machine consumers need stable, validated metadata independent of prose (adr-0002). | The README documents identity, lifecycle, versions, config namespace, resources, capabilities, authorities, relationships, providers, and adoption mode with a full example. | Must |
| FR-003 | The standard shall define an `adoption` mode vocabulary that classifies every one of the seven current standards. | Today's outliers (`project-spec` CLI-enforced, `python-coding` draft) must be first-class, not special cases. | The enum includes at least `validator`, `copy-adopt`, `cli`, `reference-only`, and `none`, and the README maps each current standard to a mode. | Must |
| FR-004 | The standard shall define authority-tuple declarations and the mutating-conflict rule. | Conflict-free composition cannot be proven from prose alone (adr-0004). | The README defines the tuple `(domain, target, concern, owner, mutates)` and states that two mutating authorities over the same concern and overlapping target with different owners conflict unless an ADR-backed `extends` relation exists. | Must |
| FR-005 | The standard shall define the relationship taxonomy and the independent-package default. | Hidden hard dependencies break arbitrary adoption (adr-0013). | The README defines `independent`, `companion`, `extends`, `conflicts`, and `consumes_platform`; declares `independent` the default; and forbids a hidden `requires` edge. | Must |
| FR-006 | The standard shall define config-namespace ownership as **dotted namespace paths**, supporting both top-level and nested ownership with parent delegation, and shall reserve non-standard meta keys. | `.project-standards.yml` already nests ownership (`markdown.frontmatter` vs `markdown.adr` under one `markdown` key) and carries meta keys, so top-level-only ownership cannot model the repo (adr-0008). | The README defines a namespace as a dotted path; states that a parent namespace (e.g. `markdown`) may be a shared container whose child paths are owned by different standards; reserves meta keys (`standards_version`) as repo-owned, not standard-owned; and declares duplicate ownership of the _same_ path invalid. The model must represent `markdown.frontmatter` (markdown-frontmatter), `markdown.adr` (adr), `spec` (project-spec), and `standards_version` (meta) without duplicate-owner ambiguity. | Must |
| FR-007 | The standard shall define provider-hook declarations for generic operations. | Standard-specific behavior must be pluggable, not hardcoded (adr-0006). | The README documents a provider declaration (operation, kind, entrypoint, optional) covering validate, fix, drift-check, id generation, and extraction. | Should |
| FR-008 | The standard shall define resource descriptors for lazy-loadable bundle content. | Future resource/MCP consumers must reference stable identifiers (adr-0010). | The README documents URI-safe resource IDs that map to bundle file paths. | Should |
| FR-009 | The standard shall define the lifecycle states and the ADR-backed exception process. | Tooling must know draft/active/deprecated status; deviations need auditability. | The README documents `draft → review → active → deprecated → archived` (plus `superseded`) and requires exceptions to be recorded as ADRs. | Should |
| FR-010 | The standard shall ship its own `standard.toml` as a worked example plus a blank `templates/standard.toml`. | The repository dogfoods the contract it defines. | `standards/standard-bundle-authoring/standard.toml` exists and conforms to the contract; a blank `templates/standard.toml` ships. | Must |
| FR-011 | The standard document shall itself conform to the repository's Markdown Frontmatter, Markdown Tooling, and Project Specification standards. | Dogfooding — the meta-standard must meet the bar it sets. | The README carries canonical frontmatter and passes `validate-frontmatter`, markdownlint, and Prettier; this spec passes `spec validate` and `spec lint`. | Must |
| FR-012 | The standard shall require manifest-declared paths to be safe and bundle-contained, and providers to be first-party and local. | Future tooling trusts manifest resources and providers; standard resources are bundle resources (adr-0010), a path outside the bundle must fail per `SPEC-MT01`, and the adopt engine already enforces bundle-relative containment. | The README requires resource and template paths to be **bundle-relative and contained within the declaring standard's own directory** (no `..`, no absolute paths, no symlink escape), permitting cross-bundle sharing only through the explicit shared-artifact (`_shared`) mechanism; treats a provider `entrypoint` as an import path or command reference, not a filesystem path; requires providers to be first-party and to perform no network access by default; and requires a missing optional provider to be declared explicitly rather than inferred. | Must |
| FR-013 | The standard shall define how `standard.toml` links to the artifact plane. | Step 04 graph validation must reason about artifact ownership and collisions without re-inventing the adopt engine (adr-0003). | The README requires each `standard.toml` to either reference its `adopt.toml` artifact manifest or explicitly declare non-adoptability, and states that artifact ownership, shared artifacts (`_shared`), and destination-collision semantics remain delegated to the artifact plane. | Must |
| FR-014 | The standard shall include a manual `standard.toml` conformance checklist, pending the Step 03 schema. | With no schema yet, "conforms to the contract" (FR-010) is otherwise circular; a checklist makes conformance objectively decidable and gives Step 03 an explicit baseline to preserve or supersede. | The README maps every required `standard.toml` field to the worked example; the checklist is owner-acceptable; and Step 03 must preserve it or record a deliberate supersession. | Must |

---

> **Sections §8–§16 are Standard/Full-tier** (Architecture, Data Model, Behavior, UI/API, Errors, Security, Capacity, Risks, Compliance) and are intentionally omitted at the Light profile.

## 17. Testing and Acceptance

### 17.1 Definition of Done

- [ ] `standards/standard-bundle-authoring/README.md` defines the full bundle contract (FR-001…FR-014) with one annotated `standard.toml` example.
- [ ] The `adoption`-mode vocabulary classifies every current standard, including `project-spec` (`cli`) and `python-coding` (`reference-only`, draft).
- [ ] The config-namespace model (FR-006) represents `markdown.frontmatter`, `markdown.adr`, `spec`, and `standards_version` without duplicate-owner ambiguity.
- [ ] Manifest path/provider safety rules (FR-012) and the `adopt.toml` linkage / non-adoptability marker (FR-013) are documented.
- [ ] `standards/standard-bundle-authoring/standard.toml` exists and passes the manual conformance checklist (FR-014); a blank `templates/standard.toml` ships.
- [ ] `standards/README.md`'s bundle-anatomy text is updated so `adopt.md` is required only for _adoptable_ standards (internal/reference/cli standards use an explicit non-adoptable marker) — not merely a new table row.
- [ ] OQ-001 (adoption-mode name) and OQ-002 (worked-example completeness) are resolved in §21.
- [ ] The README carries canonical Markdown frontmatter and passes `validate-frontmatter`, markdownlint, and Prettier; it is listed in `standards/README.md`.
- [ ] This spec passes `spec validate` and `spec lint`.
- [ ] No machine schema, model, or validator is introduced (deferred to Steps 03–04); `registry.json` is unchanged.
- [ ] Deviations Log reviewed and accepted by owner.
- [ ] No known blocking defects.

---

> **Sections §18–§20 are Standard/Full-tier** (Deployment, Implementation Plan, Success Evaluation) and are intentionally omitted at the Light profile.

## 21. Open Questions and Decisions

| ID | Question | Current Assumption | Blocking? | Owner | Needed By | Status |
| --- | --- | --- | --- | --- | --- | --- |
| OQ-001 | Should `project-spec`'s adoption mode be named `cli` or a broader `package-tooling`? | **Decided: `cli`.** It names how the standard is actually enforced today; broaden to `package-tooling` only via a spec revision if a second CLI-enforced standard appears. Not schema-binding until Step 03. | No | Owner | Step 03 schema | Answered |
| OQ-002 | Should the meta-standard's own `standard.toml` be a full annotated example or a minimal identity-only one? | **Decided: a complete annotated example** (identity + config namespace + at least one authority + `adoption = "none"`), so it doubles as documentation; the manual conformance checklist (FR-014) maps each required field to it. | No | Owner | Authoring | Answered |

---

## Deviations Log

| ID      | Spec Reference | Deviation          | Reason        | Approved? |
| ------- | -------------- | ------------------ | ------------- | --------- |
| DEV-001 | N/A            | No deviations yet. | Initial draft | Pending   |

---

## Appendix A: ID Conventions

Stable IDs allow requirements to be referenced from commits, tests, issues, ADRs, and review comments — and let an implementer's completion claims be mechanically checked. Section numbers below match `spec-full-template.md`, so an ID keeps the same "Defined In" reference across every profile.

| Prefix | Meaning                     | Defined In     |
| ------ | --------------------------- | -------------- |
| `NG-`  | Non-goal (never)            | §2.2           |
| `WH-`  | Won't have in v1 (deferred) | §2.3           |
| `FR-`  | Functional requirement      | §7.1           |
| `OQ-`  | Open question               | §21            |
| `DEV-` | Deviation                   | Deviations Log |

Higher-tier ID prefixes (`G- A- C- NFR- IR- DR- D- AW- EC- ERR- R- MS-`) are defined in the Standard/Full templates. Priority values (`Must/Should/Could`) are column values, not ID prefixes — IDs never change when priorities do.

---

## Appendix B: Agent Implementation Contract

Binding when this spec is implemented by a coding agent. (Applies equally well to human contractors.)

### B.1 Implementation Rules

The implementer shall:

- Read this entire specification before making changes; per session thereafter, re-read at minimum §7 (Requirements), §21 (Open Questions), and the Deviations Log.
- Preserve all explicit non-goals and won't-haves.
- Treat **Must** requirements as mandatory and **blocking** open questions as hard stops for the affected work.
- On encountering underspecified behavior: file an `OQ-` row **with a proposed default assumption** and proceed on it only if non-blocking — never guess silently.
- On any divergence from the spec: record a `DEV-` row (spec reference, what, why) rather than adapting silently.
- Add or update tests for every implemented requirement.
- Prefer small, reviewable changes; avoid broad refactors unless the spec requires them.
- Document any discovered mismatch between the spec and existing code as a `DEV-` or `OQ-` row.

### B.2 Prohibited Behaviors

The implementer shall not:

- Invent requirements not present in this spec.
- Remove existing behavior unless explicitly required.
- Introduce external services or dependencies not agreed with the owner without an approved `OQ-`.
- Store secrets in source control or print them in CI logs.
- Ignore failing tests unrelated to the change without documenting them.
- Treat examples as exhaustive or normative unless explicitly stated.
- Mark a requirement complete without a test or check that proves it.

### B.3 Required Completion Report (verification gate)

At completion, provide:

- Summary of changes and files changed.
- **Each Must requirement mapped to the test or command that proves it.** Claims without verification are not accepted.
- Tests added or changed.
- Deviations (`DEV-` rows) and their approval status.
- Known limitations and remaining open questions.
- Documentation updated (README / usage).

### B.4 Session Handoff

For multi-session implementations: record in-progress requirement IDs and unresolved `OQ-`/`DEV-` items in the repository's session-state/handoff documents at the end of each session, per the repo's documentation convention. The spec records _what and why_; handoff docs record _where work stands_.

---

> **Appendix C (Optional Modules) is Full-tier** — external-integration, scheduling, entity-resolution, and scoring modules — and is intentionally omitted at the Light profile.

## Appendix D: Upgrading This Spec

Pick the smallest profile that fits; upgrade if the project grows.

| Upgrade to | When | Adds |
| --- | --- | --- |
| **Standard** (`spec-standard-template.md`) | Typical features and services | §3 Context, §4 Goals, §6 Glossary, §7.2–§7.4, §8 Architecture, §9 Data Model, §10 Behavior, §11 UI/API, §12 Error Handling, §13 Security, §17.2–§17.3 Testing, §18 Deployment, §19 Implementation Plan, References |
| **Full** (`spec-full-template.md`) | Multi-service systems, durable data, external integrations, or multiple stakeholders | Everything in Standard plus §5 Stakeholders, §8.4 Alternatives, §8.6 Dependency Policy, §14 Capacity, §15 Risks, §16 Compliance, §18.4 Rollout Controls, §20 Success Evaluation, §19 Waves, and Appendix C optional modules |

Because numbering is stable across profiles, upgrading is **additive**: insert the missing sections at their canonical numbers, set `profile:` in the frontmatter, and no existing section or ID reference has to change.
