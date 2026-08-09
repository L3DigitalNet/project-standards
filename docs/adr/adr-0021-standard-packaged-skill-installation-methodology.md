---
schema_version: '1.1'
id: 'adr-0021-project-standards-standard-packaged-skill-installation-methodology'
title: 'ADR 0021: Standard-Packaged Skill Installation Methodology'
description: 'Records the decision that skills shipped by standard packages install into the consuming project, not global agent or user-level locations.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-08-09'
reviewed: '2026-08-09'
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
  - 'standards/standard-bundle-authoring/versions/2.0/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/adopt.md'
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
  - 'docs/adr/adr-0022-standard-packaged-hook-installation-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
supersedes: []
superseded_by: null
source:
  - 'standards/standard-bundle-authoring/versions/2.0/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/adopt.md'
  - 'standards/markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/SKILL.md'
  - 'standards/markdown-frontmatter/versions/1.2/payload.toml'
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
  amends:
    - 'adr-0016-project-standards-package-markdown-frontmatter-skill-with-standard'
  amended_by:
    - 'adr-0023-project-standards-unified-consumer-standards-control-plane'
---

# ADR 0021: Standard-Packaged Skill Installation Methodology

MADR status: **accepted**.

> **Amended by ADR 0023 (2026-07-10).** The project-local `.agents/skills/<skill-id>/` destination and standard ownership remain in force. The unified control plane becomes the installation entry point, and the central lock owns applied provenance, drift, update, shared references, and safe removal instead of package-specific adoption state.
>
> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings O1, O2, O3, and O4).** Three narrowings and no new authority. The validation-exclusion rule loses its open-ended "or other standards" tail and now binds only the paths this record declares. The escalation clause distinguishes an in-population exception from an out-of-scope case. The outcome states explicitly that this record reserves `.agents/skills/` only and does not own the `.agents/` root. This record is also the class rule that generalizes [ADR 0016](adr-0016-package-markdown-frontmatter-skill-with-standard.md); that relationship is now recorded on both records.

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

If a future supported agent requires a different project-local skill path, that destination may be added only when it remains inside the consumer repository or project and is declared explicitly in the selected payload manifest. The policy is project-local installation, not one hard-coded directory name forever.

This record reserves `.agents/skills/` and nothing more. It does not own the `.agents/` root: it does not decide who creates that directory, what else may live directly under it, whether a future artifact class may claim a sibling subtree such as `.agents/<something-new>/`, or who adjudicates two packages wanting the same subtree. [ADR 0022](adr-0022-standard-packaged-hook-installation-methodology.md) reserves `.agents/hooks/` on the same terms. Ownership of the root itself is **reserved authority**: it is undecided, it requires its own decision record before any package claims a new subtree, and until then a new artifact class is governed by neither this record nor ADR 0022.

The standard package remains the canonical owner of the skill. Under Catalog 5, a standard-owned skill lives under `standards/<id>/versions/<version>/skills/<skill-id>/`; the version's `payload.toml` declares its source, digest, policy, and project-local destination. The symlink-only `src/project_standards/payloads/<id>/<version>/` projection carries those canonical bytes into built distributions and must pass projection and package-parity checks. Historical V1 copies under unversioned family roots or `src/project_standards/bundles/<id>/` remain migration evidence only and do not define the current package.

Installed skills are agent harness artifacts, not managed project documents. A consumer repository must exclude installed skill paths from managed Markdown frontmatter validation, formatting, linting, type checking, or other standards when those tools would interpret the skill files as ordinary project content. The adopting standard may seed those exclusions when needed.

That requirement binds exactly the installed skill paths this record declares. It is not a rule about the consumer's managed corpus generally: which other paths a consumer governs, and under which standards, is the consumer's own configuration decision. A standard this record does not name is not bound by it, and a consumer document outside an installed skill path requires no exception here.

Global or home-level skill installation may still exist as a separate workstation convenience. That operation must be opt-in, documented outside the standard adoption path, and never required for a repository to comply with a standard. A global copy must not be treated as the source of truth for a standard-packaged skill.

Graph validation, payload-manifest validation, projection checks, and package tests should enforce this boundary where possible. A standard package that declares a skill artifact with a global destination is invalid unless a later ADR creates a narrow exception.

That exception path exists for an **in-population** case: a standard-packaged skill that must, for a stated reason, install somewhere this record prohibits. It is not required for a case this record never governed. A skill that no standard package ships, a personal global skill a user maintains outside standard adoption, and an artifact that is not a skill are all out of scope, and none of them needs an ADR, exception, or waiver under this record. Changing the project-local policy, the declared destination form, or the global-installation prohibition is an amendment to this record; adding a project-local destination for a newly supported agent under the rule already stated above is ordinary reviewed work and requires none.

### Consequences

- Good, because standard adoption does not mutate user-global or machine-global agent state.
- Good, because each adopting repository carries the skill version that matches its adopted standard package.
- Good, because skills become reviewable, reproducible project artifacts rather than hidden workstation prerequisites.
- Good, because cloned repositories, CI-like agent environments, and other maintainers can receive the same agent operating layer.
- Neutral, because users may still maintain personal global skills outside the standard adoption contract.
- Bad, because multiple repositories may contain duplicate installed skill copies and need explicit reconciliation, upgrade, and drift-check behavior.

## More Information

- Standard bundle authoring contract: [`standards/standard-bundle-authoring/versions/2.0/README.md`](../../standards/standard-bundle-authoring/versions/2.0/README.md)
- Markdown Frontmatter Standard skill guidance: [`standards/markdown-frontmatter/versions/1.2/README.md`](../../standards/markdown-frontmatter/versions/1.2/README.md)
- Markdown Frontmatter adoption procedure: [`standards/markdown-frontmatter/versions/1.2/adopt.md`](../../standards/markdown-frontmatter/versions/1.2/adopt.md)
- Markdown Frontmatter payload manifest: [`standards/markdown-frontmatter/versions/1.2/payload.toml`](../../standards/markdown-frontmatter/versions/1.2/payload.toml)
- ADR 0001, standard bundle authoring contract: [`adr-0001-standard-bundle-authoring-contract.md`](adr-0001-standard-bundle-authoring-contract.md)
- ADR 0003, separate standard and artifact manifests: [`adr-0003-separate-standard-and-artifact-manifests.md`](adr-0003-separate-standard-and-artifact-manifests.md)
- ADR 0005, stable generic agent and tooling interface: [`adr-0005-stable-generic-agent-tooling-interface.md`](adr-0005-stable-generic-agent-tooling-interface.md)
- ADR 0007, standard graph validation gate: [`adr-0007-standard-graph-validation-gate.md`](adr-0007-standard-graph-validation-gate.md)
- ADR 0010, standard resource URIs and index: [`adr-0010-standard-resource-uris-and-index.md`](adr-0010-standard-resource-uris-and-index.md)
- ADR 0016, Markdown Frontmatter skill ownership: [`adr-0016-package-markdown-frontmatter-skill-with-standard.md`](adr-0016-package-markdown-frontmatter-skill-with-standard.md)
- ADR 0017, unified standard adoption methodology: [`adr-0017-unified-standard-adoption-methodology.md`](adr-0017-unified-standard-adoption-methodology.md)
- ADR 0019, packaged artifact parity and provenance: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
- ADR 0020, standard package versioning methodology: [`adr-0020-standard-package-versioning-methodology.md`](adr-0020-standard-package-versioning-methodology.md)
