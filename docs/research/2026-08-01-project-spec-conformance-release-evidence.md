---
schema_version: '1.1'
id: 'research-mdxbi8-project-spec-conformance-release-evidence'
title: 'Project Specification Conformance Release Evidence'
description: 'EV-009: unpublished child-plan completion evidence for Project Specification conformance linting.'
doc_type: 'research'
status: 'active'
created: '2026-08-11'
updated: '2026-08-11'
reviewed: '2026-08-11'
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'project-spec'
  - 'conformance'
  - 'verification-evidence'
aliases:
  - 'EV-009'
related:
  - 'docs/plans/2026-08-01-open-issue-resolution-program-plan.md'
  - 'docs/plans/2026-08-01-project-spec-conformance-plan.md'
  - 'docs/research/2026-08-01-project-spec-conformance-dogfood-evidence.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Project Specification Conformance Release Evidence

EV-009 records the unpublished child-plan handoff for open-issue program revision 5 task T42, requirement REQ-062, and proof TC-T42-001. It is not release or publication evidence.

## Child-plan completion

Project Specification conformance plan revision 3 validates under bridge 3.5.0 with no problems or warnings. Every active task is terminal and identity-matched:

| Task | Checkpoint | Definition digest | Proof |
| --- | --- | --- | --- |
| T1 | `b2131098672fd7af478f4edfdee87054364445b5` | `df1fea6723aa63d23e0bd98104e1654ebfec48f8ec82b1bbdf655516c805feba` | PV-T1-001 |
| T2 | `ff894721b3f106c94559cee8722451e7ece1207e` | `2f1eb7250eb653305fd20b9c8a283b3e3ff3e78157bfb398fcb6272b50667638` | PV-T2-001 |
| T3 | `318946a54acf0053ffa2e6068ba34fcf9b2808c7` | `d0ae03fd313d984abdb635e439cb3ea47d44c9f8bbf8a39c2a2cd95383609d4c` | PV-T3-001 |
| T5 | `ae6f6f4a` | `84b931668aeaf2d45ad9062ebfb1d78c7fe30903dd863bcce547ef14fc402152` | PV-T5-001 |

T4 is superseded and non-executable. Its replacement T5 consumed the preserved activation candidate and completed REQ-007 without repeating a repository-wide gate.

## Unpublished candidate state

- Project Specification 1.9 is the repository default and resolved self-host selection; 1.8 remains retained and selectable.
- The 1.9 aggregate remains `sha256:47c13ac506df6b8f053e1e2daffc4f12d060e9884a431f511d41d984deb789d8` after the separately governed runner-label advisory.
- The selected 10-document corpus is strict-clean. T5's durable EV-001 records the 406-finding RED, exact semantic-preservation comparison, source/candidate/installed zero-finding results, and reconcile convergence.
- GitHub Workflow 1.2 remains outside this checkpoint and is activated by its own plan task.

## Publication boundary

At this checkpoint, local tag `v5.19.0` does not exist, GitHub has no `v5.19.0` release, and issue #62 remains open. No release candidate was rebuilt, no repository-wide gate or hosted workflow was rerun, and no tag, asset, issue, or other external state changed for T42.

The candidate remains intentionally mutable for #55's preservation-first conversion work. Open-issue program T43 owns the single consolidated v5.19 candidate, full local gate, hosted CI, publication, artifact verification, and issue closures after #55 and the remaining v5.19 checkpoints are terminal.

## Verdict

TC-T42-001 is satisfied: the approved #62 child plan has terminal identity-matched active tasks and complete requirement/proof coverage; Project Specification 1.9 is activated but unpublished; and the handoff preserves one-release consolidation without repeating child proof or claiming publication.
