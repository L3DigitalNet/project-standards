# Project Status

## Current snapshot

- Project Standards 5.27.0 is published from release commit `3f322935`; signed `v5.27.0` and moving `v5` tags are
  live, both verified `GOODSIG`. Hosted CI on the release commit is green across every workflow.
- 5.27.0 is a four-payload correction train with no new capability: python-tooling 1.17, markdown-frontmatter 1.15,
  and project-spec 1.11 advance the pinned `astral-sh/setup-uv` action to `v10.0.1`
  ([#201](https://github.com/L3DigitalNet/project-standards/issues/201)); github-workflow 1.8 corrects the
  `Change risk` example and derives the Ready gate's refusal messages from the list the gate checks
  ([#202](https://github.com/L3DigitalNet/project-standards/issues/202), closing DEV-032). Every predecessor stays
  advertised and retained.
- The v5.27.0 assets are byte-verified: wheel `9d1c7679d4bb…` and sdist `cc7eb7f7669d…`. They are also proven
  reproducible — a rebuild from the release commit matched both digests exactly, so `uv build` is deterministic
  here. Full evidence is in `docs/handoff/deployed.md`.
- Known enforcement gap, not yet fixed: the GitHub Workflow PR-admission rule ships with no mechanism
  ([#203](https://github.com/L3DigitalNet/project-standards/issues/203)). Verified 351 commits and 0 PRs since the
  adoption commit. `CLAUDE.md`/`AGENTS.md` now require PRs for changes to `testing`; that instruction change is
  prepared on branch `policy-pr-testing` and lands as the first change admitted under the new policy.
- Three adoption reports against python-tooling 1.16 are investigated with evidence and deferred to a 1.18 payload:
  [#204](https://github.com/L3DigitalNet/project-standards/issues/204) (a real guard defect — `build_backend =
  "none"` exempts the `[project]` check that `uv lock` needs, and `adopt.md` lines 21/23 contradict each other),
  plus [#205](https://github.com/L3DigitalNet/project-standards/issues/205) and
  [#206](https://github.com/L3DigitalNet/project-standards/issues/206), both documentation gaps over mechanisms
  that already exist under the package's key-ownership invariant.
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #129
  (feature-scale); #191, re-scoped 2026-08-31 — its post-1.5 measurement window was overtaken by 1.6 and 1.7, so it
  now measures a post-1.7 window opening ~2026-09-11; #207 (release wall-clock research, Needs definition).
- Consumer-pin rollout for 5.27.0 has not started; `@v5` trackers inherit 5.27.0 automatically. The 5.26.0 rollout
  reached all 24 locally cloned consumers.
- Pre-existing consumer CI reds are unrelated and left with the owner: `llm-wiki` (gitleaks license, `spec lint`,
  two specs with malformed table delimiters), `agent-configs` (ruff testdata, legacy `doc_type` keys),
  `social-ventures` (`SL-BOILERPLATE`). Full list in `docs/handoff/deployed.md`.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
