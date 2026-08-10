# Bug Index

Generated from frontmatter. Regenerate with `python3 docs/handoff/bugs/_regen_index.py`.

| # | Date | Title | Services | Status |
|---|---|---|---|---|
| 001 | 2026-06-07 | astral-sh/setup-uv@v8 tag withdrawn — broke reusable CI | ci, github-actions | fixed |
| 002 | 2026-06-12 | markdownlint cannot see malformed GFM tables — green CI masks broken rendering | ci, markdownlint, docs | fixed |
| 003 | 2026-07-12 | release checkout used stale Git index instead of the current working tree | release, tests, git | fixed |
| 004 | 2026-08-01 | agent-handoff SessionStart failed through a rejecting Python shim | agent-handoff, claude-code, codex, python, uv | fixed |
| 005 | 2026-08-04 | agent-handoff 1.8 SessionStart never runs because args selects exec form | agent-handoff, claude-code, hooks | open |
| 006 | 2026-08-05 | create-only artifacts are invisible to drift-check, so a stale scaffold outlives its package version | control-plane, adr, reconcile, lock | fixed |
| 007 | 2026-08-09 | remote gate blocked by a redirected uv environment, and .git absence misreports as ledger corruption | rexec, tests, ledger, tooling | fixed |
| 008 | 2026-08-09 | superseded pre-format-3 checklists remained at the work-item root and were read as live executor state | execute-plan, handoff, docs | fixed |
| 009 | 2026-08-10 | active ADRs state timestamped observations about code in decision voice, so the observations go stale invisibly | adr, docs, triage | open |
