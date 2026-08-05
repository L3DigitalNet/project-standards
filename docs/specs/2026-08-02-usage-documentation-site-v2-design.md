---
schema_version: '1.1'
id: 'decision-z8v9uj-usage-documentation-site-v2-design'
title: 'Usage Documentation Site V2 design'
description: 'Approved design for an agent-maintained usage documentation site package targeted for Project Standards v5.16.0.'
doc_type: 'decision'
status: 'active'
created: '2026-08-02'
updated: '2026-08-05'
tags:
  - 'standard'
aliases: []
related: []
---

# Usage Documentation Site V2 design

## Status and provenance

- Status: `approved`
- Operation: `create`
- Decision owner: repository owner
- Created and approved: `2026-08-02`
- Revision: initial approved design
- Prior design brief: none
- Working-state source: `.project-pipeline/usage-documentation-site-v2/design-discovery/`

This brief governs new Project Specification Standard documents. The earlier SPEC-U000 through SPEC-U007 bundle and design transcript remain unchanged historical inputs.

## Problem and intended outcome

Project Standards needs a reusable package that gives repositories a local, searchable, reader-oriented usage site without exposing internal specifications, plans, research, or handoff material. Humans consume the reference; repository agents maintain it during work that changes or documents user-visible behavior.

The outcome is a Catalog 5 `usage-documentation-site` consumer package for v5.16.0. It composes with existing documentation standards, remains independent of application language, and is dogfooded here through a minimum complete reader surface.

## Current context

- The preserved July 2026 drafts established local MkDocs and Material rendering, a user-facing boundary, navigation, search, feedback, validation, and dogfood.
- They predate Standard Bundle Authoring 2.6 and contain stale registry, copy-adopt, path, configuration, and compatibility assumptions.
- CLI Documentation 1.6 owns CLI reference content and currently names `docs/usage.md`; this is a destination-path issue, not a rendering conflict.
- ADR 0027 keeps Go and Python tooling independent. Documentation tooling does not enter an adopting repository's application environment.
- The v5.15.0 boundary is approved; this work targets v5.16.0.

## Scope

### In scope

- A V2 package with `docs/usage/` as its MkDocs source boundary.
- Agent maintenance, navigation, search, feedback, local serving, strict builds, validation, transactional recovery, and dogfood.
- Composition with existing content standards and a compatible CLI Documentation successor for a site-contained canonical reference.

### Non-goals

- Editing the preserved drafts; replacing existing documentation standards; publishing all repository docs; mandatory per-tool pages; empty placeholders; a CMS or human editing workflow; inclusion in v5.15.0.

### Deferred considerations

- Hosting until a repository confirms a host and owner.
- Prose linting until observed drift justifies it.
- Required network link checking until retry and failure semantics are approved.

## Constraints and assumptions

### Constraints

- Follow the current V2 family, immutable payload, closed-option, provider, migration, and Catalog 5 contracts.
- Content standards retain authority over documents they govern.
- Package operations never overwrite or delete repository-owned prose.
- Documentation execution remains independent of application Python and Go metadata.

### Assumptions

- Existing V2 primitives can express the design. A proven gap receives the smallest generic control-plane amendment, not a package-specific engine exception.
- The pinned MkDocs version retains the approved navigation validation.
- Rescheduling from v5.16.0 would not alter the semantic design.

### Agent-applied defaults

- Keep one integrated design because package and dogfood share one outcome and release.
- Keep transient discovery state under ignored `.project-pipeline/`.

## Selected design

The package's MkDocs source is `docs/usage/`. Usage Documentation Site owns placement, navigation, rendering, search, feedback, and site validation. Applicable content standards own page layout, completeness, and generation. A CLI Documentation-conformant Markdown page is an ordinary site page; no CLI site mode exists.

Humans are read-only consumers. Managed blocks in `AGENTS.md` and `CLAUDE.md` tell agents to assess documentation impact, update canonical material in the same task, regenerate generated pages, update navigation, and run the locked strict build. Evidenced internal-only changes need no documentation churn.

The MkDocs YAML is semantically co-owned. The package owns bounded runtime, source/build, theme, required plugin or extension, validation, feedback, compatibility, and security units. Agents own site identity, `nav`, `not_in_nav`, repository links, and compatible presentation. If a required YAML unit cannot be addressed without claiming its agent-owned parent, specification work narrows package ownership to validation.

Agents curate `nav`. Strict builds reject omitted pages unless `not_in_nav` records an intentional exception. The package adds no navigation generator or duplicate orphan validator.

An executable PEP 723 script and uv script lock live under `docs/usage/.tooling/`. It exposes serve and strict-build operations. Its shebang is a Unix convenience; `uv run --script docs/usage/.tooling/usage_docs.py ...` is canonical. Adoption does not modify root Python or Go application metadata.

Feedback is the explicit choice `github-issues | disabled`; Git remotes are never used for inference. When enabled, the package owns feedback assets, the issue-form filename, and stable context-field IDs. Labels, assignees, and projects remain optional and repository-owned. Disabled mode leaves no broken feedback surface. Generalization waits for a second provider.

Only `docs/usage/index.md` is universal. It is installed create-only and then repository-owned; reconciliation requires its presence but never changes or deletes its prose. Other pages exist only when justified. The historical taxonomy is guidance, not an inventory.

For dogfood, the canonical CLI reference moves from `docs/usage.md` into `docs/usage/`. A compatible CLI Documentation successor permits this while preserving the non-site default. The site renders the canonical page directly without proxying, duplication, reshaping, or hand editing. Dogfood includes only landing page, CLI reference, navigation, GitHub feedback, and locked strict build.

Validation keeps one authority per concern: reconciliation covers options, ownership, artifacts, contributions, drift, and transaction recovery; existing Markdown standards cover metadata and Markdown quality; the locked script runs MkDocs strict checks; and a thin provider covers only otherwise-inexpressible cross-artifact invariants. Validation is read-only, and repair restores only package-owned material.

## Consequential decisions

| Decision | Approved choice | Consequence and reopening trigger |
| --- | --- | --- |
| Boundary | `docs/usage/`; content and rendering authorities remain independent. | Reopen if direct rendering needs duplicated canonical content. |
| Actors | Humans read; agents maintain docs in user-visible tasks. | Reopen if a human editorial workflow becomes real. |
| Navigation | Curated `nav`, strict omitted-page checks, explicit `not_in_nav`. | Reopen if measured scale makes curation unmaintainable. |
| Runtime | Package PEP 723 script plus adjacent uv lock. | Explicit uv invocation preserves portability. |
| Configuration | Semantic co-ownership of package infrastructure and repository identity/navigation. | Prove YAML addressability; narrow ownership if needed. |
| Feedback | Explicit `github-issues \| disabled`, no inference or framework. | Reverify GitHub behavior; generalize only for a second provider. |
| Content | One create-only repository-owned landing page; no placeholders. | Reopen if another page becomes universal. |
| CLI | Move one canonical reference into the site through a compatible CLI Documentation successor. | Inventory old links and preserve non-site defaults. |
| Validation | Compose existing authorities, thin gap provider, generic transactions. | Reopen if an invariant lacks deterministic coverage. |

The agent recommended each selected option and the repository owner explicitly approved each decision and the integrated whole.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Top-level `user-docs/` or all of `docs/` | The first fragments conventions; the second risks publishing internal docs. |
| Generated or implicit navigation | Adds machinery or makes filenames the reader experience. |
| Root project dependencies | Couples documentation to application environments and weakens Go neutrality. |
| Whole-file package MkDocs config | Conflicts with agent-owned identity and navigation. |
| Inferred or generalized feedback | Remote inference is nondeterministic; one provider does not justify abstraction. |
| Mandatory taxonomy | Creates placeholders and competes with content standards. |
| CLI proxy or copy | Adds indirection or duplicate authority instead of one migration. |
| Managed landing-page shell | Divides one reader page between owners. |
| Package end-to-end validator | Duplicates reconciliation, Markdown, and MkDocs. |

## Complexity disposition

### Retained

- MkDocs and Material, V2 lifecycle, semantic configuration ownership, the locked script, and only a proven thin provider.

### Deferred

- Hosting, prose linting, network link checking, and additional feedback providers until their recorded triggers occur.

### Rejected

- CLI site mode, generated navigation, proxies, duplicate content, managed prose shells, whole-`docs/` publication, and duplicate validators.

### Preserved extension seams

- Independent content/rendering boundaries, a successor-friendly closed feedback option, and one stable documentation command boundary.

## Unresolved decisions

### Blocking

None.

### Non-blocking

- Downstream work selects MkDocs and Material versions and proves the script lock.
- Spec authoring defines option names, schema keys, YAML scopes, artifact IDs, and provider contracts after proving generic V2 expressiveness.

## Downstream impact

- Create new specifications with new IDs and filenames; do not revise SPEC-U000 through SPEC-U007 in place.
- Specify a compatible CLI Documentation successor.
- Later v5.16.0 planning owns implementation, dogfood, old-path link migration, and handoff/release index updates.

## Sources

- `docs/specs/usage-documentation-site/` — preserved drafts and transcript.
- `standards/standard-bundle-authoring/versions/2.6/README.md` — V2 architecture.
- `standards/cli-documentation/versions/1.6/README.md` and `payload.toml` — CLI profiles and path convention.
- `docs/plans/2026-08-01-open-issue-resolution-program-plan.md` — v5.15.0 boundary.
- `docs/adr/adr-0027-adopt-go-alongside-python-with-neutral-tooling.md` — neutral tooling ownership.
- MkDocs configuration and writing guides — navigation and strict validation.
- Material getting-started and uv script guides — reproducible isolated execution.
- GitHub issue-form schema and syntax guides — form location, field IDs, and metadata.

## Spec-authoring handoff

- Design brief: `docs/specs/2026-08-02-usage-documentation-site-v2-design.md`
- Operation: `create`
- Status: `approved`
- Problem and outcome: Create a v5.16.0 V2 package for a local, searchable, agent-maintained usage reference with a strict user-facing boundary.
- Scope boundary: Site infrastructure, composition, feedback, validation, lifecycle, and dogfood are included; hosting, prose linting, network checking, human editing, and bulk internal-doc publication are not.
- Selected design: `docs/usage/`, semantic MkDocs ownership, locked PEP 723 tooling, curated strict navigation, explicit feedback, repository-owned prose, direct CLI composition, and layered validation.
- Approved consequential decisions:
  - Human readers and agent maintainers.
  - CLI content authority remains with CLI Documentation.
  - Curated navigation, explicit feedback, create-only landing page, and one canonical site-contained CLI reference.
  - Isolated tooling, semantic configuration, layered validation, and generic transaction recovery.
- Agent-applied defaults:
  - One integrated downstream initiative.
- Assumptions:
  - Existing V2 primitives suffice or receive the smallest generic amendment.
  - v5.16.0 remains the scheduling target.
- Blocking decisions: none
- Non-blocking matters:
  - Pin dependencies and formalize exact schemas and provider boundaries downstream.
- Downstream impact:
  - Create new specs, including the CLI Documentation successor; later update v5.16.0 planning and indexes.
- Material source artifacts:
  - `docs/specs/usage-documentation-site/`
  - `standards/standard-bundle-authoring/versions/2.6/README.md`
  - `standards/cli-documentation/versions/1.6/README.md`
  - `docs/adr/adr-0027-adopt-go-alongside-python-with-neutral-tooling.md`
