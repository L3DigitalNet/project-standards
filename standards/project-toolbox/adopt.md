# Adopt the Project Toolbox Standard

The current consumer package is [`project-toolbox@1.0`](versions/1.0/adopt.md). Use it in a repository whose periodic maintenance sweeps should follow one written, versioned procedure: it delivers two workflow documents under `.standards/packages/project-toolbox/workflows/` and a routing skill into both `.agents/skills/project-toolbox/` and `.claude/skills/project-toolbox/`.

There are no prerequisites beyond an initialized `project-standards` consumer repository. The package requires no other standards package, no particular language or toolchain, and no forge account.

## Configure and reconcile

The package has no configuration options; enabling the family installs its complete inventory.

```bash
project-standards standards enable project-toolbox --version 1.0
project-standards reconcile
project-standards reconcile --apply
```

Reconciliation is offline and deterministic; rerunning it converges rather than accumulating changes. It delivers six managed whole-file artifacts. The two skill trees are byte-identical copies of one payload source, because Claude Code discovers project skills only under `.claude/skills/` while Codex uses `.agents/skills/`. Commit all six.

## Verify and troubleshoot

```bash
project-standards reconcile --check --json
```

A clean result reports `ok: true`, `drift: false`, and no findings. `reconcile --check` exits `1` when drift exists — that non-zero exit is the preview reporting a difference, not a tool failure.

The package installs no command to run. Confirm delivery by listing `.standards/packages/project-toolbox/workflows/`, then load the `project-toolbox` skill in an agent session and let it route you to the sweep you need.

A hand edit to any delivered file is reported as `CP-MODIFIED-MANAGED` drift. The workflow documents are package-owned; improve them through a new package version rather than in place.

## Composing with other standards

Both workflows open by reading `.standards/config.toml` to learn which packages the repository has installed, then fold each installed package's own gates and conventions into the sweep. Adopting more standards therefore makes these sweeps stronger without any configuration change here. With nothing else installed, both documents degrade to their generic checks and remain usable.
