---
schema_version: '1.1'
id: 'adr-0029-project-standards-agents-root-allocation'
title: 'ADR 0029: .agents Root Allocation'
description: 'Allocates the platform-owned .agents root by artifact class while preserving shared consumer and package use of each allocated subtree.'
doc_type: 'adr'
status: 'active'
created: '2026-08-10'
updated: '2026-08-10'
reviewed: '2026-08-10'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'agent'
  - 'architecture'
  - 'standard'
  - 'standards-platform'
aliases:
  - 'ADR 0029'
  - '.agents root allocation'
related:
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
supersedes: []
superseded_by: null
source:
  - 'https://github.com/L3DigitalNet/project-standards/issues/159#issuecomment-5235656273'
  - 'docs/adr/adr-0016-package-markdown-frontmatter-skill-with-standard.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
  amends: []
  amended_by: []
---

# ADR 0029: .agents Root Allocation

MADR status: **accepted**.

## Context and Problem Statement

ADRs 0021 and 0022 allocate `.agents/skills/` and `.agents/hooks/` to standard-packaged skills and hooks, respectively. Both records deliberately reserve authority over the `.agents/` root for a separate decision. ADR 0016 also binds one managed destination under the skills subtree without governing the root.

Package-managed and consumer-authored content already coexist below `.agents/`. The skills subtree uses a flat `<skill-id>` namespace shared by packages and the consumer, while hooks use `<standard-id>` directories. A future package has no recorded authority to create a sibling subtree for a new artifact class, and no root-level decision currently chooses how such a subtree avoids collisions between packages.

This decision governs allocation of immediate artifact-class subtrees under the project-local `.agents/` root in repositories that adopt the standards platform. It applies when the platform or a standard package proposes a new artifact class below that root, and when a package places content in a subtree the platform has already allocated. It does not govern package source trees, harness-specific roots such as `.claude/` or `.codex/`, user-global agent configuration, or the content contract within the existing skills and hooks classes. It changes no installed path.

Who allocates `.agents/` subtrees, and how do standard packages and consumer-authored content coexist within them?

## Decision Drivers

- Preserve the root authority expressly reserved by the existing skills and hooks decisions.
- Let packages and consumers coexist without granting a package exclusive ownership of shared directories.
- Give future artifact classes a collision-resistant package key before delivery work depends on one.
- Preserve the installed skill paths already used by consumers.
- Keep allocation policy separate from each artifact class's content and lifecycle contract.

## Considered Options

- **Make the root platform-owned and allocate it per artifact class** - require a class decision before allocating a new subtree, give new classes a common package key, and preserve existing classes.
- **Leave the root deliberately unowned** - let each package claim a subtree without a platform allocation decision.
- **Fold root ownership into ADR 0023** - widen the consumer control-plane record to govern agent-harness artifact layout.
- **Defer allocation until a third artifact class appears** - retain the current skills and hooks decisions without a root owner.

## Decision Outcome

Chosen option: **make the root platform-owned and allocate it per artifact class**.

The standards platform owns allocation of immediate artifact-class subtrees under `.agents/` in an adopting repository. A new artifact class requires its own ADR before a standard package may claim a new `.agents/<artifact-class>/` subtree. That class ADR defines the class boundary and destination contract. Adding content within an already allocated class is ordinary reviewed work when the owning class decision permits it and the package declares its exact payload destination.

Within an allocated subtree, a package owns only the exact destinations its selected payload declares. It never owns the containing class subtree. Consumer-authored and vendored content may coexist there, and its presence is not drift or a policy violation under this record.

New artifact-class subtrees key standard-packaged content by `standard-id`, using destinations beneath `.agents/<artifact-class>/<standard-id>/`. The existing `.agents/hooks/<standard-id>/` layout already follows this rule. The existing `.agents/skills/<skill-id>/` flat namespace is grandfathered: ADRs 0016 and 0021 continue to govern those installed skill destinations, and this record neither relocates nor rekeys them. The resulting possibility that a package skill ID collides with consumer-authored or vendored content is an accepted risk.

This decision applies only to allocation and package use of artifact-class subtrees under the project-local `.agents/` root. It does not relocate existing content, alter the skills or hooks content contracts, grant ownership of consumer-authored bytes, govern package source trees, or govern project-local and global harness paths outside `.agents/`. Those cases require no exception to this ADR. Changing an existing class's key space or repairing the grandfathered skill namespace is also outside this allocation decision and requires separately reviewed authority.

### Consequences

- Good, because a package cannot establish a new shared root convention by being first to ship it.
- Good, because packages and consumers can coexist in one allocated class without ambiguous subtree ownership.
- Good, because new classes use a consistent package key that prevents package-to-package name collisions.
- Neutral, because each future class needs one ADR before its first subtree is allocated.
- Bad, because the grandfathered skills namespace retains a known collision risk.
- Bad, because root allocation and class behavior remain split across related records that reviewers must read together.

### Confirmation

A change is in scope when it proposes a new immediate artifact-class subtree under `.agents/` or a standard-packaged destination within an allocated class. A new class conforms when an accepted ADR allocates it before a package uses it and standard-packaged destinations key by `standard-id`. Work within an existing class conforms when its class ADR permits the destination and the package claims only its declared paths. Existing skill destinations are confirmed against ADRs 0016 and 0021 under the grandfathered rule; changes outside `.agents/` receive no finding under this record.

## Pros and Cons of the Options

### Platform-owned allocation per artifact class

- Good, because one authority adjudicates new shared subtrees before packages depend on them.
- Good, because class-specific decisions stay bounded to their artifact populations.
- Bad, because introducing a class has a documentation checkpoint before implementation.

### Deliberately unowned root

- Good, because a package could introduce a new class without a separate allocation decision.
- Bad, because it contradicts the reserved authority in ADRs 0021 and 0022.
- Bad, because no owner would adjudicate competing package claims.

### Root ownership in ADR 0023

- Good, because it would reuse an active platform record.
- Bad, because agent-harness artifact layout is outside ADR 0023's governed population, so the change would widen that decision.

### Defer allocation

- Good, because no third artifact class exists today.
- Bad, because the decision would be made under delivery pressure and the live mixed-ownership skills subtree would remain unexplained.

## More Information

- ADR 0016, package Markdown Frontmatter skill with standard: [`adr-0016-package-markdown-frontmatter-skill-with-standard.md`](adr-0016-package-markdown-frontmatter-skill-with-standard.md)
- ADR 0021, standard-packaged skill installation methodology: [`adr-0021-standard-packaged-skill-installation-methodology.md`](adr-0021-standard-packaged-skill-installation-methodology.md)
- ADR 0022, standard-packaged hook installation methodology: [`adr-0022-standard-packaged-hook-installation-methodology.md`](adr-0022-standard-packaged-hook-installation-methodology.md)
