---
schema_version: '1.1'
id: 'decision-6ttbqe-project-toolbox-package-design'
title: 'project-toolbox standard package design'
description: 'Approved design for the project-toolbox Catalog 5 consumer package: proven cross-cutting workflows delivered as managed checklists with a routing skill.'
doc_type: 'decision'
status: 'active'
created: '2026-08-16'
updated: '2026-08-16'
tags:
  - 'standard'
aliases: []
related: []
---

# project-toolbox standard package design

## Status and provenance

- Status: `approved`
- Operation: `create`
- Decision owner: repository owner
- Created and approved: `2026-08-16`
- Revision: 1.0 — initial owner approval of the integrated design after ADR/SBA reconciliation.
- Prior design brief: none
- Work-state anchor: [#168](https://github.com/L3DigitalNet/project-standards/issues/168) (v5.21.0)

## Problem and intended outcome

Proven cross-cutting workflows and tools — repository housekeeping, drift detection, and similar assets that fit no existing package or span two or more standards — exist only as personal practice. Packaging them as a Catalog 5 consumer family makes them versioned, distributable, reconciled, and drift-checked across consumer repositories. The family is also the foundation for two sequenced future programs: template-repository autopopulation (to be reframed around catalog profiles and reconciliation after this package ships) and the `agent-managed-repo` standard.

## Current context

- Issue #168 anchors the work; its acceptance criteria were deliberately absent until this design cycle. The package ships activated in the v5.21.0 release train.
- The only prior recorded intent is `docs/TODO.md`: a "provider-neutral `project-toolbox` standard, including its proven workflows and routing skill."
- Structural precedent: eight consumer families; the nine-site new-family integration surface (`docs/handoff/conventions.md` §19, `scripts/family_preflight.py`); the `github-workflow` family's self-hosted proving pattern.

<!-- release-consistency: historical standard-bundle-authoring -->

- Authority reconciliation (2026-08-16): every consequential decision below was checked against the ADR corpus and Standard Bundle Authoring 2.6; none is constrained into a different shape. Binding constraints are listed with their decisions.

## Scope

### In scope

- One consumer family, `project-toolbox@1.0`, the durable home for proven cross-cutting or otherwise homeless workflows and tools.
- v1.0 inventory, deliberately minimal to prove the family shape: a repository-housekeeping workflow, a drift-detection workflow, and a routing skill as the front door.
- Self-hosting: this repository adopts the package as part of its release train.

### Non-goals

- Template-repository autopopulation and `agent-managed-repo` (sequenced after this package).
- Executable tooling: no Python providers, no scripts, no binaries in v1.0.
- Per-tool configuration options.

### Deferred considerations

- Additional toolbox tools — trigger: family shape proven by the v1.0 release.
- Per-tool option gates — trigger: the inventory grows enough that consumers want selective adoption.
- A verify provider for drift detection — trigger: a mechanical fail-closed check becomes necessary rather than instructional guidance.

## Constraints, assumptions, and agent-applied defaults

Constraints (binding recorded authority):

- ADR 0021 (amended 2026-08-15): every skill artifact installs at both `.agents/skills/<skill-id>/` and `.claude/skills/<skill-id>/` as byte-identical, digest-locked managed copies; project-local only.
- ADR 0023: package-owned durable resources live under `.standards/packages/project-toolbox/`, declared, committed, inventoried, and drift-checked; the package must not require another standard for config, adoption, or a shared container.
- SBA 2.6 mandatory furniture: exactly one canonical standard document, one agent summary, one closed config schema, and one adoption guide; aggregate-digest and immutability rules apply. A brand-new family declares no migrations, legacy states, or legacy signatures.
- ADR 0006: supplying no provider implementation must be explicit, not a silent no-op.

Assumptions:

- Provider-neutral means the packaged assets serve both Claude Code and Codex CLI consumers; the dual-tree skill install satisfies this.

Agent-applied defaults (low consequence, reversible):

- Family id `project-toolbox`, first version `1.0`.
- Standard package furniture authored per SBA templates.
- The SBA 2.6 authoring guide predates the dual-tree skill rule (#173); the payload is authored from ADR 0021 and the `markdown-frontmatter`/`agent-handoff` payload precedent instead.

## Selected design

One consumer family, `project-toolbox@1.0`, delivering three assets and the mandatory furniture:

- **Repository-housekeeping workflow** and **drift-detection workflow**: Markdown checklist and guidance documents installed as managed whole-file artifacts at `.standards/packages/project-toolbox/workflows/`.
- **Routing skill**: the front door that routes an agent to the right toolbox workflow, installed as byte-identical dual-tree copies under `.agents/skills/` and `.claude/skills/`, including an `openai.yaml` harness config in both trees (matching the three existing skill-shipping packages).
- **Configuration**: all-or-nothing. Enabling the family installs everything; the config schema is a closed object with no options.
- **Dependency posture**: requires no other standards package. The workflow documents instruct the operator or agent to consult `.standards/config.toml` and fold installed packages' own gates and conventions into the sweeps — composing existing machinery, never duplicating it.
- **No Python providers** (explicit), no `AGENTS.md`/`CLAUDE.md` contribution block, no migrations.
- **Self-hosted**: this repository enables the family in its own `.standards/config.toml` on release, proving install, reconcile, and drift coverage through its own consumer path.

## Consequential decisions

Each decision below was approved by the owner on 2026-08-16; reconciliation classified all as supported by recorded authority.

1. **Contents and posture** — the toolbox holds proven cross-cutting or homeless workflows and tools; soft dependency (nothing required, installed packages taken into account). Supported by ADR 0013 (independently adoptable by default) and ADR 0023 (must not require another standard for platform needs). Reopen if the posture proves unimplementable in the payload contract.
2. **v1.0 inventory** — housekeeping + drift detection + routing skill, deliberately minimal. Reopen if authoring shows one of the three is not extractable as a proven asset.
3. **Delivery form** — Markdown checklists/guidance as managed artifacts; routing skill dual-tree. The dual-tree shape is mandatory under amended ADR 0021, not stylistic. Alternatives (skills plus a verify provider; executable script artifacts) were presented and declined as disproportionate for v1.0.
4. **Placement** — `.standards/packages/project-toolbox/workflows/`, per ADR 0023's package-owned-resources rule and the `agent-handoff`/`markdown-frontmatter` precedent.
5. **Structure** — one family, not one per tool; later tools are additive minors and avoid repeated nine-site integration cost.
6. **Configuration** — all-or-nothing; a closed empty options schema is a precedented SBA shape. Owner selected this over the agent's per-tool-gates recommendation; gates remain addable later without breaking the family.
7. **openai.yaml** — ship unconditionally in both trees, matching existing skill-shipping packages; #175 will settle org-wide gating policy and the family conforms alongside the others when it does.
8. **Self-hosting** — adopt in this repository on release (github-workflow precedent; consistent with ADR 0011 dogfood-fixture intent and the repository's dogfooding non-negotiable).

## Alternatives considered

- **Pipeline/orchestration contents** (design→execute skill chain, agent roster): rejected by the owner's definition of the package — the toolbox holds cross-cutting homeless assets, not the pipeline.
- **Family per tool**: rejected — each new family pays the full nine-site integration surface; disproportionate for checklist documents.
- **Skills plus a Python verify provider**: deferred — stronger assurance for drift detection, but provider code, schemas, and tests are premature for an unproven family shape.
- **Executable script artifacts**: rejected — lifecycle burden (script drift, cross-platform) disproportionate for guidance documents; agents are the intended operators.
- **Per-tool option gates**: declined by owner in favor of all-or-nothing simplicity at this inventory size.

## Complexity disposition

### Retained

- One new family and its mandatory SBA furniture — required to distribute anything at all.
- Dual-tree byte-identical skill install — mandated by amended ADR 0021.
- Doubled artifact declarations for every skill file — the only conforming dual-tree shape.

### Deferred

- Per-tool option gates — reconsider when the inventory grows and consumers want selectivity.
- Additional tools — reconsider after v1.0 proves the family shape.
- Drift-detection verify provider — reconsider when instructional checking proves insufficient.

### Rejected

- Family per tool — repeated integration-surface cost with no offsetting need.
- Executable scripts — maintenance burden exceeds the value of deterministic checklists.

### Preserved extension seams

- The family itself is the seam: new tools land as additive minor versions.
- Options and providers can be introduced later without breaking consumers.

## Unresolved decisions

None blocking. Non-blocking matters, owned by specification authoring:

- Exact content and semantics of the two workflow documents (checklist items, sweep boundaries, and how each names the installed-package awareness step).
- Precise resource/artifact wiring in `payload.toml` (resource ids, digests, artifact ids and targets), following the precedent payloads.
- Whether the routing skill lists workflows statically or reads the installed workflows directory; either answer leaves the selected design unchanged.
- Verification detail: whether `SG-ARTIFACT-SKILL-DEST` (#174) reaches a Catalog-5-only family's `.claude/skills/` declarations — settle empirically by running `validate-packages` against the draft payload early in authoring.

## Downstream impact

- #168 gains acceptance criteria derived from this brief and moves through the workflow states deliberately.
- `ROADMAP.md` § 5.21.0 and the `docs/TODO.md` future-programs entries remain consistent with this design.
- The template-repo autopopulation and `agent-managed-repo` programs consume the released package; nothing in either is decided here.

## Sources

- GitHub issue #168 (work-state anchor; scope and out-of-scope statements).
- `docs/TODO.md` future-programs entries (recorded intent).
- `docs/feature-proposals/README.md` (downstream sequencing).
- `docs/adr/adr-0006`, `adr-0009`, `adr-0011`, `adr-0013`, `adr-0019`, `adr-0021` (amended 2026-08-15), `adr-0023` (governing rules cited above).

<!-- release-consistency: historical standard-bundle-authoring -->

- `standards/standard-bundle-authoring/versions/2.6/` (mandatory anatomy and furniture).
- `standards/markdown-frontmatter/versions/1.12/payload.toml`, `standards/agent-handoff/versions/1.13/payload.toml` (dual-tree skill artifact precedent).
- `docs/handoff/conventions.md` §19 (new-family integration surface).
- Owner decisions of 2026-08-16 (this design cycle).

## Spec-authoring handoff

- Design brief: `docs/specs/2026-08-16-project-toolbox-package-design.md`
- Operation: `create`
- Status: `approved`
- Problem and outcome: package proven cross-cutting workflows (housekeeping, drift detection) and a routing skill as the Catalog 5 `project-toolbox` consumer family, shipped in v5.21.0.
- Scope boundary: one family; three v1.0 assets plus mandatory furniture; no providers, options, contributions, or migrations; self-hosted on release.
- Selected design: managed Markdown workflow artifacts under `.standards/packages/project-toolbox/workflows/` plus a dual-tree routing skill with `openai.yaml`; all-or-nothing config; soft-dependency awareness via `.standards/config.toml`.
- Approved consequential decisions: contents/posture; minimal v1.0 inventory; delivery form; placement; single family; all-or-nothing config; ship `openai.yaml`; self-hosting.
- Agent-applied defaults: family id and version `project-toolbox@1.0`; SBA-template furniture; author payload from ADR 0021 + precedent payloads rather than the stale SBA 2.6 guide (#173).
- Assumptions: provider-neutral = Claude Code + Codex CLI, satisfied by the dual-tree install.
- Blocking decisions: none
- Non-blocking matters: workflow-document content; payload wiring detail; routing skill's static-versus-directory listing; #174 validator reach (verify empirically during authoring).
- Downstream impact: #168 acceptance criteria; ROADMAP § 5.21.0 and TODO consistency.
- Material source artifacts: listed under Sources above.
