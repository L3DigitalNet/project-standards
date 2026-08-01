---
schema_version: '1.1'
id: 'template-efnint-branch-integration-and-protection'
title: 'Branch Integration and Protection Strategy'
description: 'Draft ADR template for a permanent development branch, controlled main promotion, and local Git safeguards.'
doc_type: 'template'
status: 'draft'
created: '2026-08-01'
updated: '2026-08-01'
reviewed: null
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'documentation'
  - 'policy'
aliases: []
related:
  - 'docs/adr-library/README.md'
  - 'standards/adr/versions/1.3/templates/adr.md'
source: []
confidence: 'unknown'
visibility: 'internal'
license: null
---

# ADR Library: Branch Integration and Protection Strategy

## Description

This reusable draft describes a simple `dev`/`main` branch relationship and local Git-hook safeguards intended to prevent ordinary development from being committed directly to `main`.

Before adoption, confirm that the target repository uses this branch lifecycle and local enforcement model, adapt repository-specific details, add its required ADR metadata, resolve the **More Information** prompts, and obtain explicit acceptance.

```markdown
# Branch Integration and Protection Policy

## Context and Problem Statement

This repository requires a durable distinction between ordinary development and release-ready history. The permanent `dev` branch serves as the development and integration branch; `main` represents work that has been completed, tested, reviewed, and approved for promotion.

The policy must be persistent and mechanically verifiable without substituting automation for code review or owner authorization. Enforcement is intentionally local: this decision does not require pull requests, hosted branch-protection rules, or a new server-side control.

This decision ends when an approved update to `main` has been pushed successfully to its remote. Release management, tagging, artifact publication, and deployment are outside its scope. The repository may adopt or change those downstream processes without amending this ADR, provided they do not alter the branch lifecycle or local safeguard invariants defined here.

This decision defines the required branch relationship and local safeguards. It does not define their installation or implementation mechanics.

## Decision Drivers

- Keep ordinary development off `main`.
- Make the permitted promotion relationship explicit and mechanically checkable.
- Preserve existing Git-hook behavior and configuration ownership.
- Allow downstream release and publication processes to evolve independently.
- Treat client hooks as mistake prevention rather than a security boundary.

## Considered Options

- Use a permanent `dev` branch with local commit and push safeguards.
- Permit ordinary development directly on `main` and rely on manual discipline.
- Require pull requests and hosted branch protection for every promotion.

## Decision Outcome

Chosen option: "Use a permanent `dev` branch with local commit and push safeguards." This option separates routine development from release-ready history while preserving a local-only workflow.

The resulting architecture has the following invariants:

- `dev` is the permanent development and integration branch. Ordinary commits and pushes occur there without additional branch-policy restrictions.
- `main` is the protected promotion branch. It advances only by fast-forward promotion from `dev` after the work is complete, tested, reviewed, and explicitly approved by the repository owner.
- A local commit safeguard prevents ordinary direct commits on `main`.
- A local push safeguard permits an update to `main` only when local `main` and `dev` identify the same commit. It also prevents deletion and history rewrites of `main`.
- Both safeguards provide an explicit emergency bypass, but bypass use is exceptional rather than part of the normal branch lifecycle.
- Existing Git hooks and configuration outside these safeguards retain their ownership and behavior.
- Additional branches or worktrees are exceptional and require a specific isolation need; they do not replace `dev` as the integration branch.

The safeguards are advisory client-side controls. They can be bypassed and therefore prevent routine mistakes rather than establish a security boundary. Code review and owner authorization remain independent prerequisites that the safeguards do not automate.

### Consequences

- Routine development has a durable integration branch and an explicit fast-forward promotion path.
- Local mistakes are detected before they create a direct `main` commit or publish an invalid promotion.
- Existing hook behavior and configuration ownership remain independent.
- Release, tagging, publication, and deployment processes can evolve without changing this decision.
- The controls are client-side and can be bypassed intentionally.

### Confirmation

Conformance is confirmed when the observable branch and safeguard behavior satisfies the invariants above and existing Git-hook behavior remains intact. Operational documentation owns installation procedures, implementation-specific acceptance tests, and recovery instructions.

## More Information

Record links to the repository's operational hook documentation, adoption procedure, and related ownership decisions. Revisit this decision if the repository adopts server-side enforcement or changes the branch lifecycle, promotion relationship, or local safeguard invariants defined here.
```
