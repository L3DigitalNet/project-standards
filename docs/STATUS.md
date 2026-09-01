# Project Status

## Current snapshot

- Project Standards 5.27.0 is published from release commit `3f322935`; signed `v5.27.0` and moving `v5` tags are
  live, both verified `GOODSIG`, and every hosted workflow on that commit concluded `success`.
- 5.27.0 is a four-payload correction train with no new capability: python-tooling 1.17, markdown-frontmatter 1.15,
  and project-spec 1.11 advance the pinned `astral-sh/setup-uv` action to `v10.0.1`
  ([#201](https://github.com/L3DigitalNet/project-standards/issues/201)); github-workflow 1.8 corrects the
  `Change risk` example and derives the Ready gate's refusal messages from the list the gate checks
  ([#202](https://github.com/L3DigitalNet/project-standards/issues/202), closing DEV-032).
- The v5.27.0 assets are byte-verified: wheel `9d1c7679d4bb…` and sdist `cc7eb7f7669d…`. They are also proven
  reproducible — a rebuild from the release commit matched both digests exactly. Evidence in
  `docs/handoff/deployed.md`.
- **PRs are now required for every change to `testing`.** `CLAUDE.md`'s Non-Negotiables carry the admission rule
  (draft PR declaring `Final:` / `Supporting:` / `Standalone`, then `ready`, then `merge`), with T0 the sole
  exception and the release commit exempt by construction, since `scripts/release_prep.py` pins
  `RELEASE_BRANCH = "main"`. Landed as [#208](https://github.com/L3DigitalNet/project-standards/pull/208), itself
  the first change admitted under the rule.
- A long-standing CI defect is fixed ([#212](https://github.com/L3DigitalNet/project-standards/issues/212), Done):
  tests loaded payload providers by path from `standards/**` with `exec_module`, writing `__pycache__` into a tree
  whose bytes are meant to be immutable — 93 cache directories from one test file. That bumped directory mtimes and
  intermittently tripped the real-consumer-root seam canary. The guard already existed at two of twelve call sites
  and now covers all that load from the tracked tree. `real_tree_digest` was deliberately left unchanged.
- Known enforcement gap, still open ([#203](https://github.com/L3DigitalNet/project-standards/issues/203), Ready,
  P1): the _standard_ ships no mechanism behind the PR-admission rule — no `gh-workflow` subcommand, no CI workflow,
  no hook. Verified 351 commits and 0 PRs since adoption. #208 landed the documentation half only.
- Three adoption reports against python-tooling 1.16 are investigated with evidence and deferred to a 1.18 payload:
  [#204](https://github.com/L3DigitalNet/project-standards/issues/204) (a real guard defect — `build_backend =
  "none"` exempts the `[project]` check `uv lock` needs, and `adopt.md` lines 21/23 contradict each other), plus
  [#205](https://github.com/L3DigitalNet/project-standards/issues/205) and
  [#206](https://github.com/L3DigitalNet/project-standards/issues/206), both documentation gaps over mechanisms the
  package's key-ownership invariant already provides.
- Queue triaged 2026-09-01, every issue `Ready`: #209 P1 (Prettier gate exits 123 on a clean tree — the documented
  `AGENTS.md` authority is red on every checkout); #207 P2 (release wall-clock research, including the finding that
  `check.yml` has no path filter and is ~42x the next slowest PR check); #210 P2 (command-guard `--check` grants
  inert; fail-closed, so safe); #215 P2 (guarded provider-load helper plus a meta-test against an eleventh unguarded
  call site); #211 P3 (markdownlint pin, bundle with the next markdown-tooling cut).
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #129
  (feature-scale); #191, re-scoped 2026-08-31 — its post-1.5 measurement window was overtaken by 1.6 and 1.7, so it
  now measures a post-1.7 window opening ~2026-09-11.
- Consumer-pin rollout for 5.27.0 has not started; `@v5` trackers inherit 5.27.0 automatically.
- Pre-existing consumer CI reds are unrelated and left with the owner: `llm-wiki` (gitleaks license, `spec lint`,
  two specs with malformed table delimiters), `agent-configs` (ruff testdata, legacy `doc_type` keys),
  `social-ventures` (`SL-BOILERPLATE`).
