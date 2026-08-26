# Adopt Project Toolbox 1.1

Use this package in a repository whose periodic maintenance sweeps should follow one written, versioned procedure rather than personal habit.

The common V5 control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`. This guide covers project-toolbox-specific choices only.

## Prerequisites

None beyond an initialized `project-standards` consumer repository. The package requires no other standards package, no particular language or toolchain, and no forge account. It ships no executable providers, so there is no runtime, platform, or architecture prerequisite to satisfy.

## Select the configuration

| Option | Default | Purpose |
| --- | --- | --- |
| `harnesses` | `["claude-code", "codex"]` | Selected coding-agent harnesses. Controls only which skill artifacts install where a target is harness-specific — currently just the Codex-only `agents/openai.yaml` sidecar; it does not gate the routing skill itself. |

```toml
[standards.project-toolbox]
enabled = true
version = "1.1"
```

`harnesses` decides installation of the Codex-only `agents/openai.yaml` skill sidecar: it installs at `.agents/skills/project-toolbox/agents/openai.yaml` only `when_any` `harnesses` contains `codex`. Claude Code has no analogous sidecar convention and has never read it, so a `.claude/skills/project-toolbox/agents/openai.yaml` copy is never declared (issue #175). `SKILL.md` is unaffected: it keeps installing to both `.agents/skills/` and `.claude/skills/` unconditionally. The default selects both harnesses, so a repository that sets nothing keeps the Codex copy and only loses the Claude-side `openai.yaml` copy on reconcile.

## Apply and verify

```bash
project-standards standards enable project-toolbox --version 1.1
project-standards reconcile
project-standards reconcile --apply
project-standards validate
```

Reconciliation is offline and deterministic; rerunning it converges rather than accumulating changes.

Reconcile delivers five managed files by default: the two workflow documents under `.standards/packages/project-toolbox/workflows/`, the routing skill under both `.agents/skills/project-toolbox/` and `.claude/skills/project-toolbox/`, and the Codex harness interface file at `.agents/skills/project-toolbox/agents/openai.yaml`. The two `SKILL.md` copies are byte-identical, because Claude Code discovers project skills only under `.claude/skills/` while Codex uses `.agents/skills/`.

Commit all delivered files. They are repository content, inventoried and drift-checked like any other managed artifact.

## First run

Nothing to invoke — the package installs documents, not commands. Confirm the delivery instead:

```bash
ls .standards/packages/project-toolbox/workflows/
project-standards reconcile --check --json
```

A clean check reports `ok: true`, `drift: false`, and no findings. Note that `reconcile --check` exits `1` when drift exists; that non-zero exit is the preview reporting a difference, not a tool failure.

Then load the `project-toolbox` skill in an agent session and let it route you to the workflow you need.

## Living with the package

- Both workflow documents open by reading `.standards/config.toml` and folding each installed package's own gates into the sweep. Adopting more standards makes the sweeps stronger without any change here.
- The workflow documents are managed whole-file artifacts. Hand edits are reported as drift; contribute improvements upstream as a new package version instead.
- The package ships no executable providers and never mutates the repository outside reconciliation's delivery of these files. Every fix a sweep prompts is an ordinary change you make, review, and commit.
- Upgrades arrive as new package versions selected through the catalog. Version 1.1 is immutable once released.
