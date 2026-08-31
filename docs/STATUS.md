# Project Status

## Current snapshot

- Project Standards 5.26.0 is published from release commit `bc5027c0`; signed `v5.26.0` and moving `v5` tags are
  live.
- The release assets are byte-verified: wheel `0120de88b2ea…` and source distribution `ac34991eaf71…`. Full
  evidence is in `docs/handoff/deployed.md`.
- Catalog 5 this release: github-workflow 1.7 default (was 1.6), agent-handoff 1.16 default, project-spec 1.10
  default; all predecessors retained. SPEC-GHW1 rev 1.37 is current.
- github-workflow 1.7 implemented across a multi-leg engineer wave, gate-battery verified, and released same
  session. The consumer fleet migration (MS-6 item 2) completed 2026-08-31: all 24 locally cloned consumers are
  at release 5.26.0, and the five that enable the package resolve github-workflow 1.7 with byte-identical
  deployed binaries. SPEC-GHW1 has no open milestone or Definition-of-Done item.
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #191 (window
  ≥2026-09-06); #129 (feature-scale); #202 (1.7 `pr-standard.md` risk example is rejected by its own Ready gate —
  needs a 1.8 payload; DEV-032).
- Consumer-pin rollout is complete; `@v5` trackers inherit 5.26.0 automatically.
- Pre-existing consumer CI reds are unrelated to the migration and left with the owner: `llm-wiki` (gitleaks
  license, `spec lint`, two specs with malformed table delimiters), `agent-configs` (ruff testdata, legacy
  `doc_type` keys), `social-ventures` (`SL-BOILERPLATE`). Full list in `docs/handoff/deployed.md`.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
