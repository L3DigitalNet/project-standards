---
bug_id: '006'
date: '2026-08-05'
title: 'create-only artifacts are invisible to drift-check, so a stale scaffold outlives its package version'
services: '[control-plane, adr, reconcile, lock]'
status: 'open'
---

# 006 — Create-only artifacts are invisible to drift-check

**Status:** open. Diagnosed during the ADR 1.4 conformance assessment; tracked as item 1 of issue #128 for v5.18.0.

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

Not shipped. Item 1 of #128 replaces the local file and corrects the lock record. The underlying delivery gap needs a decision first: a reconcile-time create-only refresh rule, an explicit opt-in command, an `upgrade` provider operation, or a documented manual step.

If it changes reconcile behaviour it is a control-plane change rather than an ADR-package one, and it likely warrants its own ADR.

## Lesson

- Create-only is a write policy, not a provenance claim. The lock's `versions` field records which package owns a path; only `content_digest` describes bytes.
- For a create-only artifact those two fields drift apart legitimately and permanently, so `versions` must never be read as evidence of content currency.
- A green gate over a create-only artifact proves nothing about currency. Silence here means "not managed after creation", not "up to date".
- When auditing whether guidance reached its consumers, compare the installed artifact against the selected payload's declared source digest by hand.
- Neither `validate` nor `drift-check` makes that comparison for a create-only artifact.
- A package shipping guidance only through a create-only scaffold cannot revise it for anyone who adopted it. Check this at authoring time, not at audit time.
- Full analysis: `docs/reviews/adr-conformance/2026-08-05-1941-adr-1-4-conformance-assessment.md` §3 F1.
