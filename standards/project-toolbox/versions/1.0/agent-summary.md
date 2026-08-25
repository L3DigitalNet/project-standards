# Project Toolbox 1.0 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.0`; the durable home for proven cross-cutting workflows and tools that fit no single standard.
- Configuration has no options. The schema is a closed empty object, so adoption is all-or-nothing: enabling the family installs the complete inventory.
- Adoption: set `enabled = true` and `version = "1.0"` in `.standards/config.toml`, then `project-standards reconcile` and `project-standards validate`.
- Reconcile delivers six managed whole-file artifacts: two workflow documents under `.standards/packages/project-toolbox/workflows/`, and `SKILL.md` plus `agents/openai.yaml` under both `.agents/skills/project-toolbox/` and `.claude/skills/project-toolbox/`.
- The two skill trees are byte-identical copies of one payload source: Claude Code reads only `.claude/skills/`, Codex reads `.agents/skills/`. Both are digest-locked; they must never diverge.
- `repo-housekeeping.md` is the periodic hygiene sweep: branches, worktrees and their user-level tool caches, generated artifacts, dependency freshness, orphaned files, stale docs, issue and pull-request tidiness, CI health.
- `drift-detection.md` verifies the repository's actual state against what its standards, configuration, and documentation claim, including the drift classes every green gate misses.
- Both workflows begin by reading `.standards/config.toml` and folding each installed package's own gates and conventions into the sweep. Compose that existing machinery; never duplicate its checks.
- The package requires no other standards package and declares no companions, extensions, or conflicts. With nothing else installed, both workflows degrade to generic checks and remain usable.
- The package ships **no executable providers** — no provider code, no scripts, no binaries. This is explicit, not an omission; every action a sweep prompts is an ordinary reviewed change.
- No semantic contributions: the package adds no managed block to any agent-instruction file.
- No migrations, legacy states, or legacy signatures. 1.0 is a new family with no predecessor.
- New toolbox assets land as additive minor versions of this family. Per-tool option gates and a drift-detection verify provider are deferred, not rejected.
- Reconciliation is offline, deterministic, and convergent on rerun. Hand-edited managed artifacts are reported as drift and are fixed at their owner, never by re-editing the rendered file.
