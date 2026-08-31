---
schema_version: '1.1'
id: 'res-w41cls-widened-v5-15-closure-evidence'
title: 'EV-011: Widened v5.15.0 Closure Evidence'
description: 'Durable closure evidence for the widened v5.15.0 issue set (plan task T41).'
doc_type: 'research'
status: 'active'
created: '2026-08-04'
updated: '2026-08-31'
reviewed: '2026-08-05'
owner: 'Chris Purcell / L3DigitalNet'
consumer: 'agent'
tags:
  - 'release'
  - 'evidence'
aliases:
  - 'EV-011'
related:
  - 'Open-Issue Resolution Program Plan (docs/plans/2026-08-01-open-issue-resolution-program-plan.md, deleted under the completed-plan policy in 923cb63d)'
  - 'docs/research/2026-08-01-v5-15-release-evidence.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# EV-011: Widened v5.15.0 Closure Evidence

EV-011 for plan `2026-08-01/open-issue-resolution-program` task T41 (operational, REQ-909, TC-T41-001).

## Published release

`v5.15.0` — tagged commit `5e9bb6cc7ecb35cef069f05946ac58c31e42d595`, release <https://github.com/L3DigitalNet/project-standards/releases/tag/v5.15.0>. The release contains the Agent Handoff 1.9 successor and the T2–T7 engine corrections; full qualification and publication evidence is EV-007.

## Closure matrix (observed states, 2026-08-05)

| Issue | Task | State                                                          |
| ----- | ---- | -------------------------------------------------------------- |
| #75   | T2   | CLOSED/COMPLETED                                               |
| #90   | T3   | CLOSED/COMPLETED                                               |
| #91   | T4   | CLOSED/COMPLETED                                               |
| #101  | T5   | CLOSED/COMPLETED                                               |
| #102  | T6   | CLOSED/COMPLETED                                               |
| #107  | T7   | CLOSED/COMPLETED                                               |
| #122  | T38  | CLOSED/COMPLETED                                               |
| #123  | T39  | CLOSED/COMPLETED                                               |
| #124  | T38  | CLOSED/DUPLICATE (dispositioned against #122, not fixed twice) |

T35's original twelve (#76, #77, #83, #84, #86, #87, #89, #95, #98, #105, #106, #109) closed in the same window: eleven CLOSED/COMPLETED and #84 CLOSED/NOT_PLANNED under its accepted external-cause disposition. Every closure comment carries the release reference.

## REQ-908 consumer neutrality

A `consumer`-role repository observes no behavior change: `role` is rejected at header schema 1.0, optional at 1.1 with default `consumer`, and excluded from every configuration digest; TC-T40-001's suite proves default behavior byte-identical to 5.14.0, and the producer relaxation activates only for `role = "producer"` on advancing commands at an equal release.

## Sequencing note

T35's terminal bridge transition preceded its twelve issue writes by minutes; all twenty-one closures executed in this single post-publication window per the plan's publication-precedes-closure ordering.
