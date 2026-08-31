# Project Status

## Current snapshot

- Project Standards 5.26.0 is published from release commit `bc5027c0`; signed `v5.26.0` and moving `v5` tags are
  live.
- The release assets are byte-verified: wheel `0120de88b2ea…` and source distribution `ac34991eaf71…`. Full
  evidence is in `docs/handoff/deployed.md`.
- Catalog 5 this release: github-workflow 1.7 default (was 1.6), agent-handoff 1.16 default, project-spec 1.10
  default; all predecessors retained. SPEC-GHW1 rev 1.36 is current.
- github-workflow 1.7 implemented across a multi-leg engineer wave, gate-battery verified, and released same
  session; consumer fleet migration is deferred (MS-6 item 2, owner-coordinated).
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #191 (window
  ≥2026-09-06); #129 (feature-scale).
- Consumer-pin rollout is deferred to owner scheduling; `@v5` trackers inherit 5.26.0 automatically.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
