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
- **Every commit on `testing` or `main` carries a `Workflow-Admission` trailer.** github-workflow 1.9 replaced the
  two-class rule with four classes — `T0`, `PR #N` (written by `merge --pr N`), `handoff` (a commit touching only
  `docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md`), and `release` — and shipped the `gh-workflow admission`
  classifier, closing both [#203](https://github.com/L3DigitalNet/project-standards/issues/203) (the enforcement gap)
  and [#218](https://github.com/L3DigitalNet/project-standards/issues/218) (the handoff exemption) as Done. This
  repository declares its topology in `.standards/config.toml`: `integration_branch = "testing"`,
  `release_subject_prefix = "release:"`, and an `admission_floor` at the v5.28.0 release commit, since adoption cannot
  rewrite history. Nothing runs the classifier for us yet — the payload ships no workflow, so CI coverage is unwired.
- A long-standing CI defect is fixed ([#212](https://github.com/L3DigitalNet/project-standards/issues/212), Done):
  tests loaded payload providers by path from `standards/**` with `exec_module`, writing `__pycache__` into a tree
  whose bytes are meant to be immutable — 93 cache directories from one test file. That bumped directory mtimes and
  intermittently tripped the real-consumer-root seam canary. The guard already existed at two of twelve call sites
  and now covers all that load from the tracked tree. `real_tree_digest` was deliberately left unchanged.
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
