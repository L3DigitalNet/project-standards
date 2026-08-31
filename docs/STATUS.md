# Project Status

## Current snapshot

- Project Standards 5.26.0 is published from release commit `bc5027c0`; signed `v5.26.0` and moving `v5` tags are
  live. A 5.27.0 correction train is staged on `testing` but not prepared or published.
- The 5.27.0 stage cuts four payloads: python-tooling 1.17, markdown-frontmatter 1.15, and project-spec 1.11 advance
  the pinned `astral-sh/setup-uv` action to `v10.0.1` ([#201](https://github.com/L3DigitalNet/project-standards/issues/201));
  github-workflow 1.8 corrects the `Change risk` example and moves the accepted values into the Ready gate's finding
  message ([#202](https://github.com/L3DigitalNet/project-standards/issues/202), closing DEV-032). SPEC-GHW1 rev 1.38
  is current. Every predecessor stays advertised and retained.
- The v5.26.0 release assets are byte-verified: wheel `0120de88b2ea…` and source distribution `ac34991eaf71…`. Full
  evidence is in `docs/handoff/deployed.md`.
- github-workflow 1.7 implemented across a multi-leg engineer wave, gate-battery verified, and released same
  session. The consumer fleet migration (MS-6 item 2) completed 2026-08-31: all 24 locally cloned consumers are
  at release 5.26.0, and the five that enable the package resolve github-workflow 1.7 with byte-identical
  deployed binaries. SPEC-GHW1 has no open milestone or Definition-of-Done item.
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #129 (feature-scale);
  #191, re-scoped 2026-08-31 — its post-1.5 measurement window was overtaken by 1.6 and 1.7 before it opened, so it
  now measures a post-1.7 window opening ~2026-09-11.
- Consumer-pin rollout is complete; `@v5` trackers inherit 5.26.0 automatically.
- Pre-existing consumer CI reds are unrelated to the migration and left with the owner: `llm-wiki` (gitleaks
  license, `spec lint`, two specs with malformed table delimiters), `agent-configs` (ruff testdata, legacy
  `doc_type` keys), `social-ventures` (`SL-BOILERPLATE`). Full list in `docs/handoff/deployed.md`.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
