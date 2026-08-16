# Project Status

## Current snapshot

- Project Standards 5.20.0 is published from release commit `a7d2d688`; signed `v5.20.0` and moving `v5` tags are live.
- The release assets are byte-verified: wheel `5bd89c61…` and source distribution `82815d27…`. Full evidence is in `docs/handoff/deployed.md`.
- Claude Code skill discovery is repaired: it reads `.claude/skills/` only, never `.agents/skills/` (the Codex convention).
- agent-handoff 1.13, github-workflow 1.3, and markdown-frontmatter 1.12 install skills as byte-identical copies to both trees.
- Acceptance proven live: this repository's Claude Code session now lists all three packaged skills.
- #170, #171, and #172 are closed Done/completed. ADRs 0016 and 0021 were amended for the dual-tree contract.
- #168 (`project-toolbox`) is retargeted to 5.21.0; ROADMAP renumbered. Its design-discovery is the next major queue item.
- Open issues: #168 (Initiative, 5.21.0), #129 (deferred), #173 (SBA 2.7 doc cut, Inbox), #174 (SG-ARTIFACT-SKILL-DEST
  validator, Inbox), #175 (openai.yaml gating consistency, Inbox).
- `rexec` is now the full gate path: `[sync] git_context = true` is committed, giving read-only Git access on the worker.
- The 5.20.0 release battery ran fully remote via `rexec` (90 min serial), the first release proven end-to-end remotely.
- A transport-killed rexec run can poison the sync mirror; `rexec clean` recovers (tracked as remote-execution#9).
