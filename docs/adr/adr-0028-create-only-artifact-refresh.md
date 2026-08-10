---
schema_version: '1.1'
id: 'adr-0028-project-standards-create-only-artifact-refresh'
title: 'ADR 0028: Create-Only Artifact Refresh'
description: 'Keeps create-only artifacts permanently consumer-owned, with manual copy or editing as the only refresh and a warning for exact matches to earlier advertised content.'
doc_type: 'adr'
status: 'active'
created: '2026-08-09'
updated: '2026-08-10'
reviewed: '2026-08-10'
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

> **Amended 2026-08-09 (v5.18.0 release preparation, refutation of the selected mechanism).** The delete-and-reconcile step chosen below does not exist in the executor, so the sanctioned refresh is now a manual copy of the selected payload's artifact over the installed one. The problem, the applicability, and the exclusion of automatic refresh are unchanged. See [Amendments](#amendments).
>
> **Amended 2026-08-10 (#157 owner decision and implementation proof).** Create-only content remains permanently consumer-owned: manual copy or editing is the only refresh, and no explicit or automatic refresh path will be added. A warning now identifies unchanged content that exactly matches an earlier advertised version; customized content stays intentionally silent. This detection depends on ADR 0024 retaining every advertised immutable payload. See [Amendments](#amendments).

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

### Amendments

**Amended 2026-08-09 (v5.18.0 release preparation, refutation of the selected mechanism).** The chosen option above rests on a factual claim about the executor that release preparation disproved when it tried to perform the very refresh the Consequences section sequences for this release. Deleting `docs/adr/adr.template.md` and running `project-standards reconcile` does not recreate it. Reconcile reports `CP-CREATE-ONLY-ABSENT` — _create-only unit is absent from the repository; reconciliation records the removal in the lock and never recreates it_ — and an applied reconcile moves the unit out of `[[artifacts]]` into a permanent `[[create_only_absences]]` record in `.standards/lock.toml`. A second applied reconcile then reports the control plane as already reconciled and the file stays deleted. The "existing capability" this record selected is therefore not an existing capability, and a consumer who follows the procedure as written loses the artifact rather than refreshing it.

The sanctioned refresh is now a **manual copy**: the consumer copies the selected payload's artifact over the installed one and reviews the result as an ordinary change in its own version control. This is the same act create-only already exists to protect — an edit to a consumer-owned scaffold — so it needs no executor behavior, no absence record, and no deletion. Nothing else in this decision moves: the governed population, the applicability condition, the exclusion of automatic refresh, and the reservation of an automated path to a control-plane ADR all stand as accepted.

One consequence stated above is withdrawn with the mechanism. "The recreated artifact and the lock digest agree afterwards, so provenance stops being false" does not hold for a manual copy: `.standards/lock.toml` records a create-only unit's digest at creation time and does not recompute it on later reconciles, so after a refresh the lock keeps the creation digest while the file carries the new bytes. That disagreement is the documented steady state for a create-only artifact, not drift — reconcile plans the unit as `preserve consumer bytes outside managed changes`, `reconcile --check` stays clean, and no gate reports it. It is the same false-provenance condition this record's Context names, now understood as inherent to create-only rather than as something the refresh closes. Closing it requires the automated path this record reserves.

The Confirmation clause above is restated accordingly: the refresh is confirmed when the installed bytes match the selected payload's declared source bytes. The clause requiring `.standards/lock.toml` to record that same digest is withdrawn, because no supported operation produces it.

**Amended 2026-08-10 (#157 owner decision and implementation proof).** The automated-path reservation is closed. Create-only is permanently non-overwriting, and neither reconcile, a dedicated refresh command, nor a package provider may replace installed create-only content. Manual copy or editing remains the only sanctioned refresh because it expresses the consumer's decision as an ordinary reviewable repository change. The advisory-free variant is also rejected: the control plane now reports `CP-CREATE-ONLY-STALE` when a selected, materialized static create-only unit exactly matches the equivalent unit from a strictly earlier advertised package version.

The advisory is observational only. It does not refresh content, change the lock, create drift, or turn validation into a failure. Content matching the selected version is current and silent. Customized or otherwise unmatched content, content matching only a later advertised version, absent content, and provider-generated content without an immutable source digest are also silent. In particular, silence for a customized copy does not prove that it is current; determining whether consumer edits should be carried forward remains a manual review.

The historical comparison depends on [ADR 0024](adr-0024-catalog-scoped-package-version-channels.md): every advertised version must remain available with its immutable embedded payload. Those payloads, rather than Git history or `.standards/lock.toml`, are the currency oracle. Removing an earlier advertised payload would make unchanged content from that version indistinguishable from customization and would weaken the advisory without changing the write policy.

The Confirmation clause is restated again for the settled outcome. The advisory confirms staleness only when the installed semantic content exactly matches the nearest strictly earlier advertised version of the selected create-only unit. A manual refresh is confirmed separately by comparing the installed content with the selected payload source; lock metadata is not evidence of create-only content currency.

## More Information

Sequencing for this repository's own scaffold: `docs/adr/adr.template.md` was refreshed during release preparation for v5.18.0, **after** the Catalog 5 default for `adr` moved to 1.5, by the manual copy the amendment above sanctions. Performing it earlier would have copied the 1.4 template, because the source is whichever payload the repository currently resolves — which is why the order matters. The original wording of this paragraph attributed the copy to reconcile; that attribution is what the amendment refutes.

- Conformance assessment recording finding F1: [`2026-08-05-1941-adr-1-4-conformance-assessment.md`](../reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md)
- Control plane, reconcile, and lock authority: [`adr-0023-unified-consumer-standards-control-plane.md`](adr-0023-unified-consumer-standards-control-plane.md)
- Artifact provenance classes: [`adr-0019-packaged-artifact-parity-and-provenance.md`](adr-0019-packaged-artifact-parity-and-provenance.md)
- Package channels and permanent version advertisement: [`adr-0024-catalog-scoped-package-version-channels.md`](adr-0024-catalog-scoped-package-version-channels.md)
