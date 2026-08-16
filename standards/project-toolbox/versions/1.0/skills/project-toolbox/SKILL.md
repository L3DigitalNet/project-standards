---
name: project-toolbox
description: Use when running a periodic repository housekeeping sweep or checking whether the repository's actual state still matches what its standards, configuration, and documentation claim; routes to the packaged Project Toolbox workflow documents.
compatibility: Claude Code and Codex CLI
license: MIT
metadata:
  author: Chris Purcell
  version: '1.0'
---

# Project Toolbox

Project Toolbox is the home for proven cross-cutting workflows that belong to no single standard. This skill is the front door: it routes you to the right workflow document, which is the authority for how the work is done.

## Choose a workflow

| Use when | Workflow |
| --- | --- |
| Periodically clearing repository debris — dead branches and worktrees, stale caches, drifting dependencies, orphaned files, stale docs, abandoned issues and pull requests, unhealthy CI | `.standards/packages/project-toolbox/workflows/repo-housekeeping.md` |
| Verifying the repository's actual state matches what its standards, configuration, and documentation claim — including drift that every green gate misses | `.standards/packages/project-toolbox/workflows/drift-detection.md` |

Read the chosen document and follow it. Work its checklist in order and do not summarize it back from memory; the gotchas it records are the reason it exists.

The two overlap at the edges — housekeeping notices stale documentation, drift detection confirms it. When both apply, run housekeeping first: it removes the debris that would otherwise be reported as drift.

## Dependency posture

Project Toolbox requires no other standards package. Each workflow opens by reading `.standards/config.toml` to learn which packages are installed, then folds each installed package's own gates and conventions into the sweep — composing existing machinery rather than duplicating it. With no packages installed, both workflows degrade to their generic checks and still apply.

## Boundary

The package ships documents only: no executable providers, no scripts, no binaries. It plans and finds work; it never mutates the repository on its own. Every fix a sweep produces is an ordinary change you make, review, and commit.
