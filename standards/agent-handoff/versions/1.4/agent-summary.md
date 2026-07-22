# Agent Handoff Standard: Agent Summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

Lifecycle: active. Adoption: V5 reconciliation with typed scaffold and upgrade support.

## Use this summary when

Start or close an agent session, route a durable repository fact, change handoff files, adopt the standard, or investigate conformance drift. Use the installed [repo-local skill](skills/agent-handoff/SKILL.md) for the operating procedure.

## Core rules

- The adopting repository is the complete authority boundary. Do not read sibling repositories or workstation-global state for project handoff.
- Consumer knowledge is create-only; standard-owned skills, hooks, package policy, and bounded integration entries are centrally locked. Preserve user-authored tasks and unrelated instruction or configuration content.
- Do not reread `state.md` when SessionStart already injected it. In manual mode, read it and inspect Git state.
- Keep current facts eager and route durable detail by lifetime:

| Fact | Owner |
| --- | --- |
| Current snapshot | `docs/STATUS.md` |
| User and agent work queues | `docs/TODO.md` |
| Next-session focus and active incidents | `docs/handoff/state.md` |
| Deployment truth | `docs/handoff/deployed.md` |
| Stable architecture and patterns | `docs/handoff/architecture.md`, `conventions.md` |
| Credential references, never values | `docs/handoff/credentials.md` |
| Active spec and plan pointers | `docs/handoff/specs-plans.md` |
| Compact history and durable lessons | `docs/handoff/sessions/YYYY-MM.md`, `bugs/NNN-slug.md` |

- At closeout, update only changed facts, move completed work out of eager state, preserve user work, append compact history when useful, validate, and review the diff.
- Automatic Claude Code and Codex profiles use the same repository-local hook. Manual mode supports other agents without claiming automatic injection.
- Instruction-file budgets exclude only exact central-lock-authenticated managed Markdown envelopes; ambiguous or unauthenticated lookalikes count.

## Commands and artifacts

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
project-standards agent-handoff legacy-report --repo . --json
project-standards agent-handoff upgrade --repo . --dry-run --json
```

## Boundaries and companions

Agent Handoff does not own workstation configuration, global hooks or skills, credentials, fleet rollout, sibling repositories, or consumer-authored knowledge after creation. Store credential names and retrieval references only.

## Canonical resources

Read the [standard](README.md), [adoption and maintenance guide](adopt.md), and [legacy migration guide](resources/legacy-migration.md).
