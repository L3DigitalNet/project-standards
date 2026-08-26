# Project Toolbox family: Agent Summary

Current authority is the Catalog 5 consumer payload [`project-toolbox@1.1`](versions/1.1/agent-summary.md). Its [versioned standard](versions/1.1/README.md) and the installed workflow documents win over this mutable navigation summary.

- The family is the durable home for proven cross-cutting workflows and tools that fit no single standard. Version 1.1 ships two workflow documents, a routing skill, and a `harnesses` option that gates the Codex-only `openai.yaml` skill sidecar.
- Load the packaged `project-toolbox` skill to choose a sweep, then read and follow the workflow document it routes to; do not summarize a sweep back from memory.
- `repo-housekeeping.md` is the periodic hygiene sweep. `drift-detection.md` verifies the repository's actual state against what its standards, configuration, and documentation claim.
- Both sweeps begin by reading `.standards/config.toml` and folding each installed package's own gates and conventions into the work. Compose that machinery; never duplicate its checks.
- The package has one configuration option, `harnesses`, and requires no other standards package. With nothing else installed, both workflows degrade to generic checks and remain usable.
- The package ships no executable providers, scripts, or binaries. It finds work; every fix it prompts is an ordinary change you make, review, and commit.
- All delivered files are managed whole-file artifacts. Hand edits are reported as drift and are fixed at their owner, never by re-editing the rendered file.
- `SKILL.md` is installed twice, byte-identically, under `.agents/skills/project-toolbox/` and `.claude/skills/project-toolbox/`; the copies must never diverge. `agents/openai.yaml` is a Codex-only descriptor with no Claude Code counterpart, gated `when_any` `harnesses` contains `codex` (issue #175).

Verify with `project-standards reconcile --check --json`, which is clean only at `ok: true`, `drift: false`, and no findings. See the [current adoption guide](adopt.md) for enabling, applying, and troubleshooting.
