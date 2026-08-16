# Project Status

## Current snapshot

- Project Standards 5.21.0 is published from release commit `a625091c`; signed `v5.21.0` and moving `v5` tags are live.
- The release assets are byte-verified: wheel `155d56f1…` and source distribution `c8812f20…`. Full evidence is in
  `docs/handoff/deployed.md`.
- New Catalog 5 consumer family `project-toolbox@1.0` shipped (ninth consumer package): two managed workflow
  checklists (repo-housekeeping, drift-detection) plus a routing skill installed dual-tree with `openai.yaml`.
- This repository self-hosts `project-toolbox`: enabled in `.standards/config.toml`, reconciled clean (`drift:false`).
- #176 (check-release baseline loader accepting same-path-same-digest declarations) was found and fixed in-train.
- #168 and #176 are closed Done/completed. ADR-governing design brief:
  `docs/specs/2026-08-16-project-toolbox-package-design.md`.
- Open issues: #129 (deferred), #173 (SBA 2.7 doc cut, Inbox), #174 (SG-ARTIFACT-SKILL-DEST validator, Inbox — gained
  in-train evidence that it cannot reach catalog-native families, only legacy V1 bundles), #175 (openai.yaml gating
  consistency, Inbox).
- Follow-up filed: `L3DigitalNet/remote-execution#10` (rexec misreports a wedged mirror deletion as tree instability).
- `rexec` is the full gate path; the 5.21.0 release battery ran fully remote in ~31 minutes, coverage 90%.
- A pending owner decision: add `.claude/worktrees/` to `[sync].exclude` in `.rexec.toml` to prevent recurrence of
  the mirror wedge seen in remote-execution#10; not yet applied.
