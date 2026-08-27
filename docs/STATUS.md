# Project Status

## Current snapshot

- Project Standards 5.24.0 is published from release commit `3a387543`; signed `v5.24.0` and moving `v5` tags are
  live.
- The release assets are byte-verified: wheel `d78af85c…` and source distribution `5902cd91…`. Full evidence is in
  `docs/handoff/deployed.md`.
- Catalog 5 this release: markdown-frontmatter 1.14 default (1.13 retained), landing review findings
  F1/F2/F4/F5/F7/F11, #194 (generic provider-registry test), #195 (`CP-VERIFY` path+kind).
- #178 resolved: v519 plan repointed then retired; GSF3 plan re-authored as format 3 + spec 0.2. A repo-wide docs
  drift audit (partitions A–F) retired ten completed plans; `docs/plans/` now holds only the GSF3 master.
- Post-tag fixes landed directly on `main` at `c7757b49` (pushed; `testing` fast-forwarded): spec-lint
  HTML-comment false positive, payload-tree tests ignoring `__pycache__`, usage-doc-site conformance (90→0) + D-003,
  issue-regression ledger amendments for the payload_tree sweep (`482de306`/`afffa83e`), and the 100-order
  compatibility-sweep ceiling recalibrated 40s→60s (`2e62d576`/`c7757b49`; self-hosted 44.7s, not a regression).
- Hosted CI on `c7757b49`: Validate Specs, Format, Coherence, Lint Markdown, graph, and project-standards checks are
  green; Check was still in_progress when this session closed (only the recalibrated perf lane remained).
- Issues closed Done/completed: #194 #195 #178. Deferred: #129 (feature-scale), #191 (window ≥2026-09-06).
- Filed this session: #196 (frozen provider comments, Ready), #197 (v4 bundle + family-root skill, Needs
  definition), #198 (preserve semantics, Needs definition), #199 (project-spec 1.10 cut, Ready), #200 (stale
  characterization digests, Ready); `agent-configs#69` and `agent-configs#70`.
- Owner inputs pending: SPEC-GSF3 OQ-001 (blocks that plan's T1), #197, #198.
- `verify.sh --full` ran remote ~100 min with 7 reds, all classified (worker `__pycache__`, test pins, skill
  mirror); file reruns green. The `rexec` worker went unreachable twice (ssh timeout) but recovered on retry.
- Consumer-pin rollout is deferred to owner scheduling; `@v5` trackers inherit 5.24.0 automatically.
- Consumer repos still on `.agents`-only skill trees (`agent-ventures`, `llm-wiki`) per the session-corpus review's
  F2.
