---
bug_id: '006'
date: '2026-08-05'
title: 'create-only artifacts are invisible to drift-check, so a stale scaffold outlives its package version'
services: '[control-plane, adr, reconcile, lock]'
status: 'fixed'
---

# 006 — Create-only artifacts are invisible to drift-check

**Status:** fixed for v5.19.0 (`d8d5c52f`). ADR 0028 now makes the no-refresh decision permanent. The control plane warns when unchanged create-only content exactly matches an earlier advertised version, while manual copy or editing remains the only refresh.

## Symptom

This repository's `docs/adr/adr.template.md` is byte-identical to the **1.3** ADR template and contains none of the boundary prompts 1.4 introduced. Every ADR authored here since 1.4 shipped started from the wrong scaffold.

At discovery, nothing reported it. `uv run project-standards validate` exited `0`, reconcile planned no change, and `drift-check` found nothing. The lock appeared to assert that the file was current:

```toml
[[artifacts]]
path = "docs/adr/adr.template.md"
owners = ["adr"]
versions = { adr = "1.4" }
policy = "create-only"
content_digest = "sha256:f6ac2567…"   # the 1.3 template's bytes
```

while `payloads/adr/1.4/payload.toml` declares the artifact with source digest `sha256:e8129bc6…`.

## Cause

Two correct behaviours combine into a blind spot.

`policy = "create-only"` means the executor writes the artifact if it is absent and never touches it again. That is right for a scaffold the consumer edits — reconcile must not overwrite an author's template customisations.

The lock records `content_digest` from **what was installed at creation**, not from the currently selected payload's source digest. Drift-check compares the live file against that recorded digest, so an untouched create-only artifact always agrees with its own record.

Before the v5.19.0 fix, no comparison used the selected and historical payloads to classify the live content. A direct comparison between the recorded digest and the selected payload's declared source digest would still be wrong: for a create-only artifact a mismatch there is the expected steady state, not a defect.

The `versions = { adr = "1.4" }` field is a **selection** record naming the package that owns the path, not a claim about content. Read casually it says the bytes are 1.4's, even though the field carries no such guarantee.

The structural consequence is broader than one file: **a package whose only managed output is a create-only artifact has no supported path to deliver a revised version of it to an existing consumer.** ADR 1.4's boundary guidance therefore reaches new adopters and nobody else — including this repository, which publishes it.

## Fix

The local scaffold was repaired in v5.18.0 (`68203eca`), and the general detection gap is fixed for v5.19.0 (`d8d5c52f`).

[ADR 0028](../../adr/adr-0028-create-only-artifact-refresh.md) was accepted with a consumer-initiated **delete-and-reconcile** as the sanctioned refresh, then **amended in the same release** because the engine refuted it.

`CP-CREATE-ONLY-ABSENT` is permanent. Deleting a create-only artifact does not make the next reconcile recreate it — absence is a terminal recorded state, not a trigger. The sanctioned refresh is therefore a **manual copy** of the payload template into the consumer path.

`docs/adr/adr.template.md` was refreshed to the `adr` 1.5 bytes that way on 2026-08-09. The lock still records the artifact's creation digest: for a create-only artifact that is correct by design, not residual drift, and it means the refresh leaves no machine-readable trace.

`CP-CREATE-ONLY-STALE` now warns when selected, materialized create-only content exactly matches the equivalent unit from the nearest strictly earlier advertised package version.

The warning reaches validation and read-only drift reporting without changing reconciliation actions, the lock, drift state, or a successful warning-only exit. It derives history from the immutable payloads that ADR 0024 requires the catalog to advertise permanently, not from Git or lock provenance.

The outcome of issue #157 is terminal: create-only stays permanently manual, and no explicit refresh, automatic overwrite, or provider refresh will be added. The advisory is deliberately conservative. Arbitrary consumer customization cannot be classified as stale or current by exact historical matching and therefore remains silent.

A consumer who wants the selected package content must review its edits and copy or edit the selected payload into place manually.

## Lesson

- Create-only is a write policy, not a provenance claim. The lock's `versions` field records which package owns a path; only `content_digest` describes bytes.
- For a create-only artifact those two fields drift apart legitimately and permanently, so `versions` must never be read as evidence of content currency.
- `CP-CREATE-ONLY-STALE` is evidence of an exact historical match, not authority to overwrite consumer content; manual copy or editing remains the remedy.
- Absence of a stale warning does not prove currency. Customized, unmatched, later-only, absent, and unsupported provider-generated content is silent.
- The advisory depends on ADR 0024's permanent advertisement of immutable payloads. The lock and Git history are not currency oracles.
- Create-only guidance cannot be forced onto adopters. Check the advisory and release notes, then review consumer changes manually.
- Full analysis: `docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md` §3 F1.
