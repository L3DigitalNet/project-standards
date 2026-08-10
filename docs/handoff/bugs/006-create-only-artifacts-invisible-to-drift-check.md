---
bug_id: '006'
date: '2026-08-05'
title: 'create-only artifacts are invisible to drift-check, so a stale scaffold outlives its package version'
services: '[control-plane, adr, reconcile, lock]'
status: 'fixed'
---

# 006 — Create-only artifacts are invisible to drift-check

**Status:** fixed in v5.18.0 (`68203eca`). The decision is recorded in ADR 0028 as amended and this repository's scaffold is current. The engine has no refresh path and is not gaining one under this bug; that is issue #157.

## Symptom

This repository's `docs/adr/adr.template.md` is byte-identical to the **1.3** ADR template and contains none of the boundary prompts 1.4 introduced. Every ADR authored here since 1.4 shipped started from the wrong scaffold.

Nothing reports it. `uv run project-standards validate` exits `0`, reconcile plans no change, and `drift-check` finds nothing. The lock even asserts the file is current:

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

The comparison that would expose the staleness — recorded digest versus the selected payload's declared source digest — is never made, because for a create-only artifact a mismatch there is the expected steady state, not a defect.

The `versions = { adr = "1.4" }` field is a **selection** record naming the package that owns the path, not a claim about content. Read casually it says the bytes are 1.4's, and nothing cross-checks the two.

The structural consequence is broader than one file: **a package whose only managed output is a create-only artifact has no supported path to deliver a revised version of it to an existing consumer.** ADR 1.4's boundary guidance therefore reaches new adopters and nobody else — including this repository, which publishes it.

## Fix

Shipped in v5.18.0 (`68203eca`), and the decision is not the one this file anticipated.

[ADR 0028](../../adr/adr-0028-create-only-artifact-refresh.md) was accepted with a consumer-initiated **delete-and-reconcile** as the sanctioned refresh, then **amended in the same release** because the engine refuted it.

`CP-CREATE-ONLY-ABSENT` is permanent. Deleting a create-only artifact does not make the next reconcile recreate it — absence is a terminal recorded state, not a trigger. The sanctioned refresh is therefore a **manual copy** of the payload template into the consumer path.

`docs/adr/adr.template.md` was refreshed to the `adr` 1.5 bytes that way on 2026-08-09. The lock still records the artifact's creation digest: for a create-only artifact that is correct by design, not residual drift, and it means the refresh leaves no machine-readable trace.

The structural delivery gap is unchanged and deliberately so. Whether reconcile grows an explicit, per-artifact, opt-in refresh — or whether create-only stays permanently manual and the investment goes into a staleness *advisory* instead — is tracked as issue #157. Either answer is a control-plane change and amends or succeeds ADR 0028.

## Lesson

- Create-only is a write policy, not a provenance claim. The lock's `versions` field records which package owns a path; only `content_digest` describes bytes.
- For a create-only artifact those two fields drift apart legitimately and permanently, so `versions` must never be read as evidence of content currency.
- A green gate over a create-only artifact proves nothing about currency. Silence here means "not managed after creation", not "up to date".
- When auditing whether guidance reached its consumers, compare the installed artifact against the selected payload's declared source digest by hand.
- Neither `validate` nor `drift-check` makes that comparison for a create-only artifact.
- A package shipping guidance only through a create-only scaffold cannot revise it for anyone who adopted it. Check this at authoring time, not at audit time.
- Full analysis: `docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md` §3 F1.
