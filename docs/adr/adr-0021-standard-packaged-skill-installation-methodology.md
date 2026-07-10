---
schema_version: '1.1'
id: 'adr-0021-project-standards-standard-packaged-skill-installation-methodology'
title: 'ADR 0021: Standard-Packaged Skill Installation Methodology'
description: 'Records the decision that skills shipped by standard packages install into the consuming project, not global agent or user-level locations.'
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
  - 'skill'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0021'
  - 'Standard-packaged skill installation methodology'
related:
  - 'standards/standard-bundle-authoring/README.md'
  - 'standards/markdown-frontmatter/README.md'
  - 'standards/markdown-frontmatter/adopt.md'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0015-exclude-standards-from-local-frontmatter-scope.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: null
source:
  - 'standards/standard-bundle-authoring/README.md'
  - 'standards/markdown-frontmatter/README.md'
  - 'standards/markdown-frontmatter/adopt.md'
  - 'standards/markdown-frontmatter/skills/markdown-frontmatter/SKILL.md'
  - 'src/project_standards/bundles/markdown-frontmatter/adopt.toml'
  - 'docs/adr/adr-0001-standard-bundle-authoring-contract.md'
  - 'docs/adr/adr-0003-separate-standard-and-artifact-manifests.md'
  - 'docs/adr/adr-0005-stable-generic-agent-tooling-interface.md'
  - 'docs/adr/adr-0007-standard-graph-validation-gate.md'
  - 'docs/adr/adr-0010-standard-resource-uris-and-index.md'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0017-unified-standard-adoption-methodology.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0020-standard-package-versioning-methodology.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
---

# ADR 0021: Standard-Packaged Skill Installation Methodology

MADR status: **accepted**.

> **Amended by ADR 0023.** The project-local `.agents/skills/<skill-id>/` destination and standard ownership remain in force. The unified control plane becomes the installation entry point, and the central lock owns applied provenance, drift, update, shared references, and safe removal instead of package-specific adoption state.

## Context and Problem Statement

Standard packages may ship agent skills. A skill is part of a standard's agent-facing operating layer: it tells an agent how to apply the standard, where the authoritative files live, what validation commands matter, and which mistakes to avoid.

ADR 0016 established this pattern for one standard-owned skill. The broader repository now needs a general methodology for every standard-packaged skill.

The main installation question is whether a standard adoption flow may install skills into user-global or agent-global locations, such as home-directory skill roots, global agent configuration, or machine-level plugin areas. Global installation is convenient for one workstation, but it creates problems for a reusable standard package:

- it affects unrelated repositories that did not adopt the standard;
- it can drift from the standard version used by a specific project;
- it is invisible to repository review, CI-like agent environments, and other maintainers' clones;
- it makes provenance unclear because the active skill may come from a workstation rather than the adopted standard package; and
- it asks a project-level adoption operation to mutate user or machine state.

Adoption is a project-level act. A consumer adopts a standard into a repository or project, and the files that shape that adoption should be local to that same boundary.

This decision governs skills shipped by standard packages as a class. It does not require every standard to ship a skill, and it does not define the full agent plugin model for every tool.

## Considered Options

- **Install standard-packaged skills globally by default** - make adopted skills available to all repositories on the user's machine.
- **Let each standard choose its own skill destination** - allow some standards to install repo-local skills and others to write global agent or user-level skill roots.
- **Require project-local installation for standard-packaged skills** - install skills only inside the consuming repository or project, and treat any global installation as a separate opt-in workstation operation.

## Decision Outcome

Chosen option: **require project-local installation for standard-packaged skills**.

Any skill shipped by a standard package and installed through standard adoption must be installed into the consuming repository or project. The default destination is `.agents/skills/<skill-id>/` at the consumer project root, because that path is discoverable by the supported agent surfaces that read repo-local shared skills.

Standard adoption tooling must not install standard-packaged skills into user-global, agent-global, home-directory, machine-level, or filesystem-root locations. It must not write to locations such as global agent skill roots, global agent configuration, `~/.agents`, `~/.codex`, `~/.claude`, or other user-level installation targets as part of normal adoption.

If a future supported agent requires a different project-local skill path, that destination may be added only when it remains inside the consumer repository or project and is declared explicitly in the package's adoption artifacts. The policy is project-local installation, not one hard-coded directory name forever.

The standard package remains the canonical owner of the skill. A standard-owned skill should live under `standards/<id>/skills/<skill-id>/`, and any packaged copy under `src/project_standards/bundles/<id>/` must follow the artifact provenance rules in ADR 0019. Adoption manifests must declare skill sources and project-local destinations explicitly.

Installed skills are agent harness artifacts, not managed project documents. A consumer repository must exclude installed skill paths from managed Markdown frontmatter validation, formatting, linting, type checking, or other standards when those tools would interpret the skill files as ordinary project content. The adopting standard may seed those exclusions when needed.

Global or home-level skill installation may still exist as a separate workstation convenience. That operation must be opt-in, documented outside the standard adoption path, and never required for a repository to comply with a standard. A global copy must not be treated as the source of truth for a standard-packaged skill.

Graph validation, adopt-manifest validation, and package tests should enforce this boundary where possible. A standard package that declares a skill artifact with a global destination is invalid unless a later ADR creates a narrow exception.

### Consequences

- Good, because standard adoption does not mutate user-global or machine-global agent state.
- Good, because each adopting repository carries the skill version that matches its adopted standard package.
- Good, because skills become reviewable, reproducible project artifacts rather than hidden workstation prerequisites.
- Good, because cloned repositories, CI-like agent environments, and other maintainers can receive the same agent operating layer.
- Neutral, because users may still maintain personal global skills outside the standard adoption contract.
- Bad, because multiple repositories may contain duplicate installed skill copies and need explicit upgrade or drift-check behavior.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/README.md`](../../standards/standard-bundle-authoring/README.md)
- Markdown Frontmatter Standard skill guidance: [`standards/markdown-frontmatter/README.md`](../../standards/markdown-frontmatter/README.md)
- Markdown Frontmatter adoption procedure: [`standards/markdown-frontmatter/adopt.md`](../../standards/markdown-frontmatter/adopt.md)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0003, separate standard and artifact manifests: [`adr-0003-separate-standard-and-artifact-manifests.md`](adr-0003-separate-standard-and-artifact-manifests.md)
- ADR 0005, stable generic agent and tooling interface: [`adr-0005-stable-generic-agent-tooling-interface.md`](adr-0005-stable-generic-agent-tooling-interface.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0010, standard resource URIs and index: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- ADR 0016, Markdown Frontmatter skill ownership: [`adr-0016-package-markdown-frontmatter-skill-with-standard.md`](adr-0016-package-markdown-frontmatter-skill-with-standard.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
- ADR 0019, packaged artifact parity and provenance: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
- ADR 0020, standard package versioning methodology: [`adr-0020-standard-package-versioning-methodology.md`](adr-0020-standard-package-versioning-methodology.md)
