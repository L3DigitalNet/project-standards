---
bug_id: '003'
date: '2026-07-12'
title: 'release checkout used stale Git index instead of the current working tree'
services: '[release, tests, git]'
status: 'fixed'
---

# 003 — Release checkout used the stale Git index

**Status:** fixed in the v5 release-readiness cleanup.

## Symptom

The disposable release-candidate proof failed after maintained specifications moved to `docs/specs/`: deleted source paths were still copied, while their untracked destinations were absent.

## Cause

`copy_tracked_checkout()` copied the cached `git ls-files` inventory. In a dirty pre-commit tree, that inventory includes tracked deletions and omits non-ignored additions, so the proof exercised neither the working tree nor the proposed commit.

## Fix

Copy `git ls-files --cached --others --exclude-standard` entries, skip paths deleted from the working tree, and preserve symlink identities. Capture that source snapshot once per proof, then derive the migration, patch-baseline, and replay trees from it. A hermetic temporary-repository test covers a tracked file, tracked deletion, and non-ignored addition.

## Lesson

- Pre-commit release proofs must model the current Git-known working tree, including non-ignored additions and excluding tracked deletions.
- Long-running proofs must use one immutable source snapshot so concurrent valid edits cannot leak into later comparison trees.
- Refresh deterministic release evidence only after lock-owned status and instruction files reach their final state.
