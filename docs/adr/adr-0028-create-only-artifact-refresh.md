---
schema_version: '1.1'
id: 'adr-0028-project-standards-create-only-artifact-refresh'
title: 'ADR 0028: Create-Only Artifact Refresh'
description: 'Selects a documented manual delete-and-reconcile step as the supported way a consumer repository refreshes an installed create-only package artifact.'
doc_type: 'adr'
status: 'active'
created: '2026-08-09'
updated: '2026-08-09'
reviewed: '2026-08-09'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'mix'
tags:
  - 'adr'
  - 'standards-platform'
  - 'control-plane'
  - 'versioning'
aliases:
  - 'ADR 0028'
  - 'Create-only artifact refresh'
related:
  - 'docs/adr/adr-0019-packaged-artifact-parity-and-provenance.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
  - 'docs/adr/adr-0024-catalog-scoped-package-version-channels.md'
  - 'docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md'
supersedes: []
superseded_by: null
source:
  - 'docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md'
  - 'docs/adr/adr-0023-unified-consumer-standards-control-plane.md'
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

# ADR 0028: Create-Only Artifact Refresh

MADR status: **accepted**.

## Context and Problem Statement

A package payload may declare an artifact with `policy = "create-only"`. That policy is correct for a scaffold the consumer is expected to edit: reconcile writes it when it is absent and never touches it again, so the consumer's edits survive every later reconcile.

The policy has a consequence nobody decided. A package whose managed output is a create-only artifact has **no supported path to deliver a revised artifact to a consumer that already has one**. Reconcile will not replace it, because create-only means exactly that. Drift-check cannot surface it, because the lock recorded whatever existed at creation, so installed and recorded state agree. If the payload later revises that artifact, the consumer keeps the old bytes indefinitely while the lock asserts current-version ownership over them — a false provenance record no gate can see.

This repository is the worked example. The [ADR 1.4 conformance assessment](../reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md) finding F1 records that `docs/adr/adr.template.md` holds the ADR 1.3 template bytes while `.standards/lock.toml` records the file under `versions = { adr = "1.4" }`. Every ADR authored here from that scaffold started from a template without the boundary prompts 1.4 introduced — which is the mechanical root cause of the boundary gap the same assessment found across the corpus.

This decision applies to create-only artifacts declared in a selected package payload and already installed in a consumer repository that adopts these standards. It does not apply to managed artifacts, whose refresh reconcile already owns, nor to consumer-owned files no payload declares. Whether the platform should ever refresh a create-only artifact _without_ the consumer asking remains undecided and is reserved to the control plane.

How should a consumer repository obtain a revised version of a create-only artifact it already has installed?

## Decision Drivers

- The consumer's edits to a scaffold must never be destroyed by a routine operation.
- A refresh must be visible and reviewable in the consumer's own history, not a silent side effect of an unrelated command.
- The lock must be able to record provenance that matches the installed bytes.
- Adding a refresh path must not change what reconcile does for artifacts that already work.
- The mechanism must be available now, offline, with no new command surface and no new executor behavior.

## Considered Options

- **A documented manual delete-and-reconcile step** — the consumer deletes the stale artifact and runs reconcile, which recreates it from the currently selected payload and records the fresh digest.
- **A reconcile-time create-only refresh rule** — reconcile detects a payload digest change and replaces the artifact automatically.
- **An explicit opt-in refresh command** — a new CLI verb that refreshes named create-only artifacts.
- **An `upgrade` provider operation** — each package implements its own refresh through the provider contract.

## Decision Outcome

Chosen option: **a documented manual delete-and-reconcile step**.

This decision governs how a revised create-only artifact reaches a consumer repository that already has an installed copy, and applies when the selected payload declares a create-only artifact whose source differs from the installed bytes and the consumer wants the package's current version. The supported refresh is exactly two consumer-initiated steps:

1. Delete the installed create-only artifact.
2. Run `project-standards reconcile`, review the plan, then `project-standards reconcile --apply`.

Reconcile then treats the artifact as absent, which is the case its existing create-only rule already handles: the executor recreates it from the currently selected payload and the lock records the fresh digest. The consumer's decision to discard local edits is expressed by the deletion, which is an ordinary reviewable change in the consumer's own version control, and the refresh is visible in the reconcile plan before anything is written.

**This decision changes no reconcile behavior.** It selects an existing capability as the sanctioned path and requires it to be documented as such; it adds no rule, no command, no provider operation, and no executor branch. A package that revises a create-only artifact must say so in its release notes or migration guidance, because that notice is the only signal an existing consumer receives.

Automatic refresh is excluded. Neither reconcile nor any other routine operation may replace an installed create-only artifact without the consumer first removing it. This decision does not govern managed artifacts, whose refresh reconcile already owns; consumer-owned files that no payload declares; the migration path defined by [ADR 0023](adr-0023-unified-consumer-standards-control-plane.md); or the provenance classes defined by [ADR 0019](adr-0019-packaged-artifact-parity-and-provenance.md). An artifact that is not create-only requires no exception to this ADR.

Reserved authority: an automated path — a reconcile-time refresh rule, a dedicated command, or an `upgrade` provider operation — remains an open control-plane question. Deciding it requires a control-plane ADR, which may supersede this record for the automated path while leaving the manual path in force for artifacts the automated path does not cover.

### Consequences

- Good, because it is available immediately, offline, with no change to the executor, the plan model, or the lock schema.
- Good, because discarding a consumer's scaffold edits is always an explicit consumer act recorded in the consumer's own history.
- Good, because the recreated artifact and the lock digest agree afterwards, so provenance stops being false.
- Neutral, because the refresh is a documentation obligation on each package rather than a platform feature.
- Bad, because a consumer who never reads the release notes keeps a stale scaffold indefinitely, and no gate reports it.
- Bad, because a consumer with substantial local edits must re-apply them by hand after the recreate.

### Confirmation

Applicability is determined first: the artifact must be declared create-only in the selected payload and already present in the consumer repository. For such an artifact, the refresh is confirmed when the installed bytes match the selected payload's declared source digest and `.standards/lock.toml` records that same digest under the selected package version. Artifacts that are not create-only receive no finding under this ADR.

## More Information

Sequencing for this repository's own scaffold: `docs/adr/adr.template.md` is refreshed by this procedure during release preparation for v5.18.0, **after** the Catalog 5 default for `adr` moves to 1.5. Performing it earlier would recreate the 1.4 template, because reconcile recreates from the payload the repository currently resolves — which is exactly the behavior this record relies on, and exactly why the order matters.

- Conformance assessment recording finding F1: [`2026-08-05-1941-adr-1-4-conformance-assessment.md`](../reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md)
- Control plane, reconcile, and lock authority: [`adr-0023-unified-consumer-standards-control-plane.md`](adr-0023-unified-consumer-standards-control-plane.md)
- Artifact provenance classes: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
- Package channels and permanent version advertisement: [`adr-0024-catalog-scoped-package-version-channels.md`](adr-0024-catalog-scoped-package-version-channels.md)
