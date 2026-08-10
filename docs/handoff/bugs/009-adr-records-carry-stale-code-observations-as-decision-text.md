---
bug_id: '009'
date: '2026-08-10'
title: 'active ADRs state timestamped observations about code in decision voice, so the observations go stale invisibly'
services: '[adr, docs, triage]'
status: 'open'
---

# 009 — ADR records carry stale code observations as decision text

**Status:** open. The two affected records are corrected by #161's amendment work; the authoring rule that produced them is not yet recorded in the `adr` package guidance.

## Symptom

ADR 0026 carries a subsection titled `#### Disclosed divergence from the shipped catalog index` describing three live resource-URI producers: a three-segment form from `standards/catalog.md`, a two-segment unversioned form from `render_catalog`, and its own four-segment wire form. It states that the forms differ and that the record does not reconcile them.

ADR 0010's amendment of 2026-08-09 repeats the claim: "That divergence is an open index-and-producer alignment item flagged for owner decision."

Both are false. Both producers were aligned on the four-segment form on 2026-07-29 in `e400f83f`, which has shipped in every release since v5.12.0:

- `src/project_standards/standards_graph/catalog.py:172`
- `src/project_standards/standards_graph/catalog.py:330`

All 1421 URIs in the shipped `standards/catalog.md` carry the four-segment form; none carry either superseded form.

## Cause

The divergence was real when ADR 0026 was accepted on 2026-07-28 and was fixed the next day. Nothing connects the fix to the record, so the observation stayed in the decision body indefinitely.

The ADR 0010 amendment is the compounding failure: written eleven days after the fix, during the #128 corpus remediation, it derived its claim from ADR 0026's disclosure section rather than from `catalog.py`. A stale observation in one record propagated into a second record dated after the evidence that disproved it.

The structural fault is voice. A disclosure subsection sits inside the Decision Outcome and reads in the same authoritative register as the decision text around it, so a reader has no signal that one paragraph is a durable commitment and the neighbouring one is a dated observation with a shelf life.

## Consequence

Issue #161 was filed to reconcile a divergence that no longer existed. Its triage initially accepted the framing, and the reconciliation half of assessment finding C1 was scoped as design work when it is documentation-only.

## Fix

#161's decision assigns grammar ownership to ADR 0026 with ADR 0010 adopting it by reference, and both amendments record the reconciliation and its commit. The records are corrected there, not here.

The authoring rule is not yet captured. An observation about code belongs in a dated amendment note, where staleness is visible, never in the Decision Outcome where it reads as a standing commitment.

## Lesson

- **An ADR states what was decided, not what the code currently does.** Live behaviour belongs in a dated amendment note, whose age is visible to a reader.
- **Agreement proves nothing when documents share an upstream source.** ADR 0010's amendment agreed with ADR 0026 because it was written from it. Bug 008 is the same shape.
- **A remediation pass inherits the errors of what it reads.** Corpus work must verify code claims against code, never against the record being remediated.
- **Check the declaration layer before calling an engine limit a blocker.** #153 was wrongly triaged as blocked on a missing lock primitive that option gating already expresses.
