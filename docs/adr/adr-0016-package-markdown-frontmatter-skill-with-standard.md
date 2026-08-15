---
schema_version: '1.1'
id: 'adr-0016-project-standards-package-markdown-frontmatter-skill-with-standard'
title: 'ADR 0016: Package Markdown Frontmatter Skill with Standard'
description: 'Records the decision that the Markdown Frontmatter Standard owns and ships its agent skill to adopting repositories.'
doc_type: 'adr'
status: 'active'
created: '2026-07-09'
updated: '2026-08-15'
reviewed: '2026-08-15'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'agent'
  - 'frontmatter'
  - 'standard'
aliases:
  - 'ADR 0016'
  - 'Markdown Frontmatter skill ownership'
related:
  - 'standards/markdown-frontmatter/README.md'
  - 'standards/markdown-frontmatter/versions/1.10/field-values.md'
  - 'standards/markdown-frontmatter/versions/1.10/adopt.md'
  - 'standards/markdown-frontmatter/versions/1.10/skills/markdown-frontmatter/SKILL.md'
  - 'standards/markdown-frontmatter/versions/1.10/payload.toml'
  - 'docs/adr/adr-0014-markdown-frontmatter-field-value-policy.md'
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0021-standard-packaged-skill-installation-methodology.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0029-agents-root-allocation.md'
supersedes: []
superseded_by: null
source:
  - 'standards/markdown-frontmatter/versions/1.2/README.md'
  - 'standards/markdown-frontmatter/versions/1.2/field-values.md'
  - 'standards/markdown-frontmatter/versions/1.2/adopt.md'
  - 'standards/markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/SKILL.md'
  - 'standards/markdown-frontmatter/versions/1.2/payload.toml'
confidence: 'high'
visibility: 'internal'
license: null
project:
  decision_makers:
    - 'chris'
  consulted: []
  informed: []
  amends: []
  amended_by:
    - 'adr-0021-project-standards-standard-packaged-skill-installation-methodology'
    - 'adr-0023-project-standards-unified-consumer-standards-control-plane'
---

# ADR 0016: Package Markdown Frontmatter Skill with Standard

MADR status: **accepted**.

> **Amended by ADR 0021 (2026-07-09).** This record is the **special case** ADR 0021 generalizes. ADR 0021 decides installation destination and the global-install prohibition for skills shipped by standard packages **as a class**, and its class rules now carry those parts of this decision for this skill as well. What remains in force here is the ownership decision: the Markdown Frontmatter package, not `agent-configs`, owns the skill. A future change to the class rule in ADR 0021 moves this skill with it; this record must not be read as pinning the old destination rule for one skill.
>
> **Amended by ADR 0023 (2026-07-10).** The Markdown Frontmatter package remains the skill's canonical owner and `.agents/skills/markdown-frontmatter/` remains its consumer destination. Selection, installation, payload provenance, drift, update, and removal move from package-specific adoption behavior to the unified control plane and central lock.
>
> **Amended 2026-08-09 (ADR 1.4 conformance assessment of 2026-08-05, findings O1, O4, and B4).** The consumer-repository validation-scope sentence in the outcome is narrowed to the population this record can bind — the installed skill's own path — and scope authority for a consumer's managed Markdown corpus is deferred to that consumer's configuration, with [ADR 0021](adr-0021-standard-packaged-skill-installation-methodology.md) stating the class rule. The ownership decision is unchanged.
>
> **Amended 2026-08-15 ([#170](https://github.com/L3DigitalNet/project-standards/issues/170)).** Destination-set extension under [ADR 0021](adr-0021-standard-packaged-skill-installation-methodology.md)'s class rule as amended the same day: from Markdown Frontmatter 1.12, reconciliation installs the skill files as byte-identical, digest-locked managed copies at both `.agents/skills/markdown-frontmatter/` and `.claude/skills/markdown-frontmatter/`, and the validation exclusion this record binds covers exactly that installed-path set. The reasoning is unchanged — an installed `SKILL.md` is agent-harness metadata, not a managed project document — and applies identically to both copies. The ownership decision is unchanged.

## Context and Problem Statement

The `markdown-frontmatter` skill previously lived in the workstation `agent-configs` repository. That made `agent-configs` appear to own an operating layer for a standard it does not define or maintain.

The skill is part of the Markdown Frontmatter Standard's consumer experience: it tells agents how to author compliant metadata, generate IDs, avoid excluded paths, and run validation. If the skill is maintained outside the standard package, it can drift from the schema, adoption procedure, field-value policy, and current validation commands.

Adopting repositories also need the skill locally. A global workstation copy does not help cloned repositories, CI-like agent environments, or other maintainers' machines.

## Considered Options

- **Keep the skill in `agent-configs`** - leave workstation configuration as the owner and require out-of-band synchronization with the standard.
- **Duplicate the skill in both repositories** - keep a copy in `agent-configs` and another copy in the standard package.
- **Package the skill with the Markdown Frontmatter Standard** - make the standard bundle the source of truth and install the skill repo-local during adoption.

## Decision Outcome

Chosen option: **package the skill with the Markdown Frontmatter Standard**, because the skill is the standard's agent-facing operating layer.

The canonical source lives under `standards/markdown-frontmatter/versions/1.10/skills/markdown-frontmatter/`. The versioned `payload.toml` declares those files as managed artifacts, and the symlink-only `src/project_standards/payloads/markdown-frontmatter/1.10/` projection carries the same bytes into the built package. Reconciliation installs them into the consuming repo at `.agents/skills/markdown-frontmatter/`.

The `.agents/` destination is intentional: both Claude Code and Codex CLI can discover repo-local shared skills there. The consuming repo must keep `.agents/**` excluded from managed-document frontmatter validation, because the skill's `SKILL.md` carries agent-skill metadata, not this standard's document metadata.

The exclusion this record binds is exactly the path it installs — `.agents/skills/markdown-frontmatter/` — and the reason is that the installed `SKILL.md` is agent-harness metadata rather than a managed project document. The class rule for every standard-packaged skill is stated by [ADR 0021](adr-0021-standard-packaged-skill-installation-methodology.md); the managed Markdown corpus of a consuming repository is that consumer's own configuration decision, which this record neither sets nor widens. A consumer document outside the installed skill path is outside this decision and requires no exception to it.

The old `agent-configs` copy is retired. Historical logs may still mention it, but `agent-configs` no longer owns, tests, inventories, or deploys this skill. That statement records the disposition of the copy this decision replaced; it is not a rule this record imposes on another repository's future contents.

### Consequences

- Good, because the skill now changes with the standard, schema, adoption guide, and field-value policy.
- Good, because every adopting repository receives the same repo-local skill path.
- Good, because global workstation skills stop being the source of truth for standard compliance.
- Neutral, because this does not change `schema_version`, frontmatter fields, controlled values, or validation outcomes.
- Bad, because changing the skill now requires updating its payload declarations and keeping source, projection, and built-package bytes aligned.

## More Information

- Decision evidence — standard-owned skill: [`markdown-frontmatter` 1.2 `SKILL.md`](../../standards/markdown-frontmatter/versions/1.2/skills/markdown-frontmatter/SKILL.md)
- Decision evidence — adoption procedure: [`markdown-frontmatter` 1.2 `adopt.md`](../../standards/markdown-frontmatter/versions/1.2/adopt.md)
- Decision evidence — payload manifest: [`markdown-frontmatter` 1.2 `payload.toml`](../../standards/markdown-frontmatter/versions/1.2/payload.toml)
- Decision evidence — package projection: [`markdown-frontmatter` 1.2 projected `SKILL.md`](../../src/project_standards/payloads/markdown-frontmatter/1.2/skills/markdown-frontmatter/SKILL.md)
