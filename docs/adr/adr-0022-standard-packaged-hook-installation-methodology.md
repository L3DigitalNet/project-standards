---
schema_version: '1.1'
id: 'adr-0022-project-standards-standard-packaged-hook-installation-methodology'
title: 'ADR 0022: Standard-Packaged Hook Installation Methodology'
description: 'Records the project-local source and installation convention for hooks shipped by standard packages.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-07-10'
reviewed: '2026-07-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'agent'
  - 'hook'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0022'
  - 'Standard-packaged hook installation methodology'
related:
  - 'docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: null
source:
  - 'docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md'
  - 'docs/reviews/2026-07-09-agent-handoff-spec-review.md'
  - 'standards/standard-bundle-authoring/README.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0022: Standard-Packaged Hook Installation Methodology

MADR status: **accepted**.

> **Amended by ADR 0023.** The project-local `.agents/hooks/<standard-id>/` destination and harness trust boundary remain in force. The unified control plane installs and updates the hook, semantically composes only declared harness registrations, and records ownership and drift in the central lock.

## Context and Problem Statement

Standard packages may ship executable agent hooks that connect a standard's project-local behavior to one or more supported harness lifecycle events. The `agent-handoff` package needs one shared SessionStart implementation for Claude Code and Codex, but this repository has no general convention for where a standard owns hook source or where adoption installs it.

Per-harness copies under `.claude/` and `.codex/` are easy to discover but duplicate one logical implementation and allow the copies to drift. A user-global hook avoids duplication but exceeds a project standard's authority, hides the active version from repository review, and makes conformance depend on workstation state. ADR 0021 resolved the same authority question for skills but does not govern hooks.

The repository needs a general, reviewable hook-installation methodology that preserves one standard-owned source, keeps every installed copy inside the adopting project, and lets multiple harness configurations reference the same implementation without transferring trust decisions to the standard.

This decision governs hooks shipped by standard packages as a class. It does not require every standard to ship a hook, define every harness registration format, or authorize hooks to execute without the consumer's normal harness trust and approval controls.

## Considered Options

- **Install separate copies under each harness directory** - place equivalent hook code under `.claude/`, `.codex/`, or other harness-specific roots.
- **Install standard-packaged hooks globally** - keep one user- or machine-level hook available to every repository.
- **Install one shared project-local hook under `.agents/hooks/`** - let supported project harness configurations reference a common repo-local implementation.
- **Let each standard choose an unconstrained destination** - require containment but establish no shared convention.

## Decision Outcome

Chosen option: **install one shared project-local hook under `.agents/hooks/`**.

A standard-owned hook's canonical authored source lives under `standards/<standard-id>/hooks/<hook-id>/`. Any distribution copy under `src/project_standards/bundles/<standard-id>/` follows ADR 0019 provenance: byte parity for a source-owned mirror or a declared deterministic transform when identity is not the correct contract.

Standard adoption installs hook files under `.agents/hooks/<standard-id>/` at the consuming project root. Harness-specific project configuration may reference that shared installed path. A package with multiple hook entrypoints may place them together under the standard's directory, while filenames remain part of that standard's declared contract.

Standard adoption must not install or inspect standard-packaged hooks in user-global, agent-global, home-directory, machine-level, filesystem-root, or sibling-repository locations. A future alternative destination requires another ADR or a superseding decision and must remain project-local unless the standard-adoption authority model itself changes.

Installed hooks are managed standard-owned artifacts. Their adopt manifest records source, destination, provenance, install policy, and executable mode. Drift validation identifies changed or stale installed hooks, and the package's owned upgrade path refreshes them only after its normal precondition and ambiguity checks. Consumer project knowledge is not a hook artifact and receives no overwrite authority from this decision.

The consuming harness retains control of registration, project trust, hook review, approval, enablement, and execution. Adoption may create or structurally merge only the exact declared project-level registration. It must not modify global trust, global hook approval, or machine policy to make the hook run.

Installed hook paths are agent harness configuration, not managed Markdown documents or consumer project knowledge. Consumer tooling should exclude them from unrelated content-management rules where appropriate.

### Consequences

- Good, because one installed implementation can serve multiple harness profiles without duplicated hook code.
- Good, because the active hook version, registration, and changes remain visible in the adopting repository.
- Good, because standard adoption stays within its project-level authority boundary.
- Good, because provenance and drift checks can identify the canonical source and installed state.
- Neutral, because each harness still needs a small project-specific registration adapter.
- Bad, because `.agents/hooks/` is a new repository convention that graph/adopt validation and documentation must learn.
- Bad, because repositories adopting the same standard contain duplicate managed hook copies and require explicit upgrades.

### Confirmation

Graph and adopt-manifest validation reject standard-packaged hook destinations outside `.agents/hooks/<standard-id>/`. Package parity tests prove canonical-to-bundled provenance. Adoption fixtures prove that multiple harness profiles reference one shared installed file, global locations remain untouched, drift is detected, and owned upgrades preserve unrelated configuration.

## More Information

- Agent Handoff v1 package specification: [`docs/superpowers/specs/2026-07-09-agent-handoff-standard-package.md`](../superpowers/specs/2026-07-09-agent-handoff-standard-package.md)
- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- ADR 0003, separate standard and artifact manifests: [`adr-0003-separate-standard-and-artifact-manifests.md`](adr-0003-separate-standard-and-artifact-manifests.md)
- ADR 0005, stable generic agent and tooling interface: [`adr-0005-stable-generic-agent-tooling-interface.md`](adr-0005-stable-generic-agent-tooling-interface.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0010, standard resource URIs and index: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
- ADR 0019, packaged artifact parity and provenance: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
- ADR 0021, standard-packaged skill installation methodology: [`adr-0021-standard-packaged-skill-installation-methodology.md`](adr-0021-standard-packaged-skill-installation-methodology.md)
