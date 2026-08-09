# Project Status

## Current snapshot

- Project Standards 5.17.0 is the published release at `29c875ab`; signed `v5.17.0` and `v5` tags are live and `uvx` from the tag reports 5.17.0.
- The release advertises `github-workflow@1.0` as the eighth consumer package and closes #132; follow-ups #143–#147 sit in Inbox awaiting triage.
- The tracker also holds the v5.18.0 ADR train (#127/#128/#129), the feature deferrals #55, #62, and #116, and the adoption/upgrade findings #130, #139–#142.
- Catalog 5 defaults: markdown-tooling 1.14, markdown-frontmatter 1.10, python-tooling 1.12, project-spec 1.8, agent-handoff 1.10, github-workflow 1.0; every predecessor remains byte-immutable and selectable.
- The full pre-tag chain including `verify.sh --full` ran green on the tagged commit; seven hosted workflows are green there and the hosted `Check` battery is in flight.
- Release assets are byte-verified: wheel `36bc8e29…`, sdist `2cfe6fe2…`.
- The open-issue program has T16, T19, and T36 terminal (checkpoints `50d0c364`, `229a4bc1`, `e13e1a66`; EV-008); the feature phase T24–T29 remains, with T24 ready.
- All four reusable workflows accept an optional `runner-labels` input for private same-organization callers.
- Reviewed action pins: setup-uv 9.0.0 (`prune-cache: true`), setup-node 7.0.0, setup-python 7.0.0.
- Dependabot stays disabled by decision; dependency currency moves through the payload cycle under the pin and width-table guards.
- The `js-yaml` override remains until `markdownlint-cli2-action` ships >= 0.23.2 (v24 still bundles 0.23.1).
- The ADR corpus was assessed against ADR 1.4: 11 of 23 active records state no boundary, five authorities contested, five boundaries unowned. See `docs/reviews/adr-conformance/`.
- v5.17.0 shipped `github-workflow@1.0` (first advertisement, `gh-workflow set --type`) and the issue #132 `runner_labels` fix; the payload is now frozen.
- The ADR train — #127 as `adr` 1.5, then the #128 corpus backlog — moves to v5.18.0 by owner direction 2026-08-08.
- The repository's `docs/adr/adr.template.md` is still the 1.3 template because create-only artifacts are invisible to drift-check (bug 006).
- All four issue #133 follow-ups are delivered: #135 (`scripts/bootstrap-worktree.sh`), #136 (candidate-wheel staleness stamp enforced in the `verify.sh` preflight), #137 (`conventions.md` #18 surface-to-verification map), and #134 (`scripts/family_preflight.py` nine-site enumerating preflight, `conventions.md` #19), plus #131 (`standards list`/`show` disclose the committed-catalog basis).
- The preflight reports `declared`/`missing`/`not applicable` per site and runs clean on all ten catalog-5 families; seam applicability is read from `AUTHORITATIVE_INPUT_OWNER`, because no `payload.toml` field separates `python-tooling` from `adr`.
- That work landed green on the full fast gate at 14:45 — statics 4:01, ordinary 9:01, compatibility 14:17, performance 0:26 — with coverage at 90%.
- #131 is the only consumer-visible item of the four and is recorded under `CHANGELOG.md` `[5.17.0]` for the v5.17.0 train; the other three are repository tooling.
- Program tail otherwise unchanged: T24–T29, SPEC-GSF3 T1, and the Usage Documentation Site V2 specs stay queued for later sessions.
- The `github-workflow` package is fully staged: approved design rev 1.6 (D0–D12) and SPEC-GHW1 rev 1.6; the format-3 plan completed 2026-08-07.
- Two Codex high-effort review rounds ran over SPEC-GHW1 and its plan; all ten round-1 findings and the round-2 residues are applied.
- `scripts/plan.py` is upgraded to the plan-authoring 3.4.0 bridge byte-identically; the open-issue program plan validates and schedules under it.
- SPEC-GHW1 OQ-001 answered: `github-workflow@1.0` ships in v5.17.0 (owner direction, 2026-08-08).
