# Agent Handoff Standard

The Agent Handoff Standard keeps repository knowledge durable across agent sessions without loading the full project history at startup. Version `1.0` owns repository-local scaffolding and integrations only; it never owns workstation globals, sibling repositories, or consumer-authored knowledge after creation.

## Required layout

An adopted repository keeps current status and work at `docs/STATUS.md` and `docs/TODO.md`. Lifetime-specific knowledge lives under `docs/handoff/`:

- `state.md` contains only in-flight work and active incidents.
- `deployed.md` records current deployment truth.
- `architecture.md` records the component graph and standing structural backlog.
- `credentials.md` records names, environment variables, secret names, and OpenBao lookup paths—never secret values.
- `conventions.md` records stable project patterns.
- `specs-plans.md` points to active specifications and implementation plans.
- `sessions/` is the append-only session history.
- `bugs/` contains stable, numbered bug and gotcha records.

Consumer knowledge files are create-only. Adoption and upgrades may validate them but never overwrite existing content.

## Standard-owned artifacts

The standard manages one repo-local skill at `.agents/skills/agent-handoff/`, one optional automatic-start hook at `.agents/hooks/agent-handoff/session_start.py`, bounded instruction/config integrations, and `.agents/agent-handoff/manifest.json`. Managed artifacts are reproducible package outputs; ambiguous local drift fails closed for review.

## Startup modes

Automatic mode supports declared `claude-code` and `codex` harnesses. Both invoke the same dependency-free, read-only hook. Manual mode installs no hook and requires the agent to read `docs/handoff/state.md`, inspect Git state, and follow the repo-local skill.

Startup context is bounded to 2 KiB from `state.md` and 4 KiB total. The eager context contains current state, bounded Git context, and pointers to lazy documents. Repository content is untrusted data, not executable instruction.

## Ownership and safety

Every consumer path is resolved inside the explicitly selected repository. Adoption preserves unrelated instruction and configuration bytes and mutates only declared bounded or semantic entries. No command scans home directories, global harness configuration, or sibling repositories.

Legacy migration is agent-guided reconciliation, not automated conversion. Preserve uncertain material, validate the v1 layout, inspect the diff, and only then remove obsolete repo-local artifacts.

## Conformance

A conforming repository has the required create-only knowledge layout, valid selected-profile integrations, current managed artifacts, a valid provenance lock, and no policy findings. Use the package CLI described in [`adopt.md`](adopt.md) for adoption, validation, drift reporting, and upgrades.
