# Project Status

## Current snapshot

- Project Standards 5.29.0 is published from release commit `14fc7f97`, fast-forwarded from `testing` `e3237c0d`;
  signed `v5.29.0` and re-pointed `v5` tags are live, both `GOODSIG`, and all eight hosted checks on that commit
  concluded `success` (Validate project standards, Validate Specs, Format, Lint Markdown, Validate standards graph,
  Go, Dependency graph, Check).
- 5.28.0 (backfilled here, never previously recorded) shipped python-tooling 1.18, markdown-tooling 1.16, and
  github-workflow 1.9 with the ADR 0031 four-class admission model; release commit `25e0094a`, GOODSIG, Latest at
  the time; closed [#203](https://github.com/L3DigitalNet/project-standards/issues/203) and
  [#218](https://github.com/L3DigitalNet/project-standards/issues/218). Full details in `docs/handoff/deployed.md`.
- 5.29.0 is an efficiency/hardening train, no new payload capability: agent-handoff 1.17
  ([#235](https://github.com/L3DigitalNet/project-standards/issues/235),
  [#229](https://github.com/L3DigitalNet/project-standards/issues/229)), github-workflow 1.10
  ([#234](https://github.com/L3DigitalNet/project-standards/issues/234), `land` subcommand, request dedup), provider
  env allowlist + `PosixMode` ([#230](https://github.com/L3DigitalNet/project-standards/issues/230)), control-plane
  perf ([#227](https://github.com/L3DigitalNet/project-standards/issues/227), `reconcile --check` 17.5s→9.5s), and a
  verification-pipeline cut ([#236](https://github.com/L3DigitalNet/project-standards/issues/236)): hosted `Check`
  main-only plus dispatch, Coherence workflow deleted, dependency graph main-only, a parallel trace-core lane, compat
  suite 150→129 rows, fail-fast, tag-only install, and a new `docs/reference/release-runbook.md`. Full battery on
  `e3237c0d`: 29:03 total vs 106 min at v5.27.0.
- Reproducibility and asset byte-verify were **not run** for 5.29.0 this cycle — periodic under owner decision D4,
  not every release.
- **Every commit on `testing` or `main` carries a `Workflow-Admission` trailer.** github-workflow 1.9 replaced the
  two-class rule with four classes — `T0`, `PR #N` (written by `merge --pr N`), `handoff` (a commit touching only
  `docs/handoff/**`, `docs/STATUS.md`, `docs/TODO.md`), and `release`. This repository declares its topology in
  `.standards/config.toml`: `integration_branch = "testing"`, `release_subject_prefix = "release:"`, and an
  `admission_floor` at the v5.28.0 release commit, since adoption cannot rewrite history. The classifier still has
  no CI wiring in this repository — the payload ships no workflow, so nothing runs it for us automatically.
- Owner decisions 2026-09-01 for this train: D1 hosted CI main-only plus one gate; D2/D3 parallel lane and compat
  trim; D4 tag-only install, no prune, R10/R11 periodic; D5 one integrated gate; handoff docs never via PR; idle
  slots do hygiene; minimize verification.
- Queue: only [#228](https://github.com/L3DigitalNet/project-standards/issues/228) P1 (payload-binary retention and
  wheel size) is `Ready`; [#228](https://github.com/L3DigitalNet/project-standards/issues/228) and
  [#236](https://github.com/L3DigitalNet/project-standards/issues/236) are being closed by a parallel triager leg.
- Follow-ups filed this train: [#253](https://github.com/L3DigitalNet/project-standards/issues/253)
  (`cut-successor` nits, P4), [#254](https://github.com/L3DigitalNet/project-standards/issues/254) (gh-workflow 1.10
  accepted residuals, P4), `remote-execution#19` (worker deletes excluded paths). Probe issue #252 was created in
  error and Dropped.
- Deferred backlog: security finding 4 (total-count evidence for array-shaped list endpoints); #129
  (feature-scale); #191, re-scoped 2026-08-31, now measuring a post-1.7 window opening ~2026-09-11.
- Consumer-pin rollout has not started for 5.28.0 or 5.29.0; `@v5` trackers inherit automatically.
- Pre-existing consumer CI reds are unrelated and left with the owner: `llm-wiki` (gitleaks license, `spec lint`,
  two specs with malformed table delimiters), `agent-configs` (ruff testdata, legacy `doc_type` keys),
  `social-ventures` (`SL-BOILERPLATE`).
