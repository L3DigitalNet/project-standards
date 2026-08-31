---
schema_version: '1.1'
id: 'research-t7kd2p-agent-handoff-1-8-closeout-evidence'
title: 'Agent Handoff 1.8 Closeout Evidence for Issue 80'
description: 'EV-001: closeout evidence for issue #80 — the reproduced 1.7 SessionStart shim failure, the 1.8 launcher-lane qualification, and the published v5.14.0 release proof the closure cites.'
doc_type: 'research'
status: 'active'
created: '2026-08-04'
updated: '2026-08-31'
reviewed: null
owner: 'project-standards'
consumer: 'agent'
tags:
  - 'agent-handoff'
  - 'issue-closeout'
  - 'verification-evidence'
aliases:
  - 'EV-001'
related:
  - 'Open-Issue Resolution Program Plan (docs/plans/2026-08-01-open-issue-resolution-program-plan.md, deleted under the completed-plan policy in 923cb63d)'
  - 'docs/STATUS.md'
source: []
confidence: 'high'
visibility: 'internal'
license: null
---

# Agent Handoff 1.8 Closeout Evidence for Issue 80

EV-001 for plan `2026-08-01/open-issue-resolution-program` task T1 (operational, REQ-080, TC-T1-001). Issue #80: "[agent-handoff] Codex SessionStart hook exits 1 when uv-strict-python shims are active."

## Reproduction (Agent Handoff 1.7, exact published bytes)

Qualified 2026-08-01 in a disposable consumer against exact `v5.13.0` / Agent Handoff 1.7 (lock pinned 1.7; installed hook byte-identical to the wheel's immutable 1.7 hook):

- All four published v1.7 direct and rendered harness launch paths (Claude and Codex) reproduced the SessionStart exit-1 failure.
- `env -i` system-Python controls against the same hook and payload succeeded for both harnesses (Claude rc=0 with valid `hookEventName=SessionStart` JSON; Codex rc=0 with a well-formed `<session_context>` document), excluding fixture parsing, hook logic, missing files, and package drift.
- The isolated difference is shebang interpreter selection: the hook resolved the rejecting uv-strict-python `python3` shim. Correct-cause reproduction confirmed.

## Successor qualification (Agent Handoff 1.8 launcher)

The 1.8 launcher's direct, uv-fallback, and unavailable-runtime lanes were qualified for both harnesses during the pre-release candidate qualification (retained logs, 2026-08-01) and again by the hosted gate on the release commit, which includes the corrected launcher fixtures.

## Published v5.14.0 release proof (independently re-observed 2026-08-04)

- Release `v5.14.0` is live, non-draft, targeting `main` at `b4be9d2e83e1fe7407b2c58b0e0ecd918075a16c`.
- Asset digests match `docs/STATUS.md` byte-for-byte: wheel `sha256:02d989a5ab543cb16c55556a645765cc549b0bde3b4600912cee438ad9b06d2e`, sdist `sha256:139808e7ff37f54b96b99b97de1a12573130053ba59014e2073f1e1bbd97aba7`.
- Hosted "Check" workflow run `30725509522`: completed, success, on the release commit.
- Signed tags live on origin: `v5.14.0` (`f73a97e9`), `v5` (`84f5cb14`).

## Closure

Owner authorization 2026-08-04 (action-specific, recorded in execution state): post one evidence comment and close #80. No release artifact was modified or republished. The closure comment cites this document and the release proof above.
