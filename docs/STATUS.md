# Project Status

## Current snapshot

- Project Standards 5.16.0 is the published release at `8a2d1b9a`; signed `v5.16.0` and `v5` tags are live and `uvx` from the tag reports 5.16.0.
- The release closed all ten open bug issues (#88–#126 defect set) and superseded the six dependency PRs.
- The tracker holds exactly the three feature deferrals #55, #62, and #116.
- Catalog 5 defaults: markdown-tooling 1.13, markdown-frontmatter 1.9, python-tooling 1.12, project-spec 1.7; every predecessor remains byte-immutable and selectable.
- The full local battery and the complete hosted fleet including `Check` ran green on the tagged commit.
- Release assets are byte-verified: wheel `02f51b12…`, sdist `bf3875f9…`.
- The open-issue program has T16, T19, and T36 terminal (checkpoints `50d0c364`, `229a4bc1`, `e13e1a66`; EV-008); the feature phase T24–T29 remains, with T24 ready.
- All four reusable workflows accept an optional `runner-labels` input for private same-organization callers.
- Reviewed action pins: setup-uv 9.0.0 (`prune-cache: true`), setup-node 7.0.0, setup-python 7.0.0.
- Dependabot stays disabled by decision; dependency currency moves through the payload cycle under the pin and width-table guards.
- The `js-yaml` override remains until `markdownlint-cli2-action` ships >= 0.23.2 (v24 still bundles 0.23.1).
- The ADR corpus was assessed against ADR 1.4: 11 of 23 active records state no boundary, five authorities contested, five boundaries unowned. See `docs/reviews/adr-conformance/`.
- v5.17.0 is scoped as the ADR train: #127 ships as `adr` 1.5, then the 21-item corpus backlog in #128. MINOR; 1.5 must stay non-breaking to become the Catalog 5 default.
- The repository's `docs/adr/adr.template.md` is still the 1.3 template because create-only artifacts are invisible to drift-check (bug 006).
- Issue #133's four follow-ups are delivered: #135 (`scripts/bootstrap-worktree.sh`), #136 (candidate-wheel staleness stamp enforced in the `verify.sh` preflight), #137 (`conventions.md` #18 surface-to-verification map), and #131 (`standards list`/`show` disclose the committed-catalog basis). #134 remains open.
- That work landed green on the full fast gate at 14:45 — statics 4:01, ordinary 9:01, compatibility 14:17, performance 0:26 — with coverage at 90%.
- #131 is the only consumer-visible item of the four and is recorded under `CHANGELOG.md` `[Unreleased]` for the v5.17.0 train; the other three are repository tooling.
- Program tail otherwise unchanged: T24–T29, SPEC-GSF3 T1, and the Usage Documentation Site V2 specs stay queued for later sessions.
- The `github-workflow` package is fully staged: approved design rev 1.6 (D0–D12), SPEC-GHW1 rev 1.2, and an active 11-task format-3 plan with T1 ready.
- Two Codex high-effort review rounds ran over SPEC-GHW1 and its plan; all ten round-1 findings and the round-2 residues are applied.
- `scripts/plan.py` is upgraded to the plan-authoring 3.4.0 bridge byte-identically; the open-issue program plan validates and schedules under it.
- Release placement for `github-workflow@1.0` is an open owner decision (SPEC-GHW1 OQ-001, post-v5.17.0).
