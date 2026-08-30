# Project Status

## Current snapshot

- Project Standards 5.25.0 is published from release commit `b2f73d9d`; signed `v5.25.0` and moving `v5` tags are
  live.
- The release assets are byte-verified: wheel `1dbc0b4ecf3d…` and source distribution `b67baaa1d9a7…`. Full evidence
  is in `docs/handoff/deployed.md`.
- Catalog 5 this release: github-workflow 1.6 default, agent-handoff 1.16 default, project-spec 1.10 default; all
  predecessors retained. SPEC-GHW1 rev 1.35 defines the approved, not-yet-implemented github-workflow 1.7 target.
- Added the tracked `main`-branch commit guard (`scripts/githooks/main-branch-guard`): only ff merges and
  `release:` commits land on `main`; override `PROJECT_STANDARDS_MAIN_COMMIT_OVERRIDE=1`.
- Fixed worker tmpfs ENOSPC via a shared payload-projection test fixture (`tests/installed_package.py`); five
  issue-ledger proof digests amended for the fixture-closure change only.
- Battery: `verify.sh --full` on the rexec worker ran 117 min (ordinary lane 58 min under full trace core).
- Issues closed Done/completed: #196 #197 #198 #199 #200. Deferred: #191 (window ≥2026-09-06), #129
  (feature-scale). DEV-004 is closed by the preserved design's dated amendment; SPEC-GSF3 OQ-001 still blocks
  that plan's T1. github-workflow 1.7 implementation has not started.
- Consumer-pin rollout is deferred to owner scheduling; `@v5` trackers inherit 5.25.0 automatically.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
