# Agent Handoff Summary

Agent Handoff version `1.0` keeps project knowledge inside the adopting repository. Use the installed [`.agents/skills/agent-handoff/SKILL.md`](skills/agent-handoff/SKILL.md) whenever a session starts or closes, a durable fact needs an owner, or handoff files are changed.

## Canonical paths

| Fact or operation | Owner |
| --- | --- |
| Current project snapshot | `docs/STATUS.md` |
| User and agent work queues | `docs/TODO.md` |
| Next-session focus and active incidents | `docs/handoff/state.md` |
| Deployment truth | `docs/handoff/deployed.md` |
| Stable architecture and boundaries | `docs/handoff/architecture.md` |
| Credential names and retrieval references | `docs/handoff/credentials.md` |
| Stable project patterns | `docs/handoff/conventions.md` |
| Active specification and plan pointers | `docs/handoff/specs-plans.md` |
| Compact session history | `docs/handoff/sessions/YYYY-MM.md` |
| Durable bug lessons | `docs/handoff/bugs/NNN-slug.md` |
| Shared automatic startup hook | `.agents/hooks/agent-handoff/session_start.py` |
| Repo-local operating procedure | `.agents/skills/agent-handoff/SKILL.md` |
| Managed provenance | `.agents/agent-handoff/manifest.json` |

Consumer knowledge is create-only. Standard-owned skills, hooks, bounded integration entries, and the provenance lock are managed.

## Operating rules

- Do not reread state already injected by SessionStart.
- In manual mode, read `docs/handoff/state.md` and inspect repository Git state.
- Read only the adopting repository for project handoff.
- Store credential references only—never values.
- Keep completed work out of eager state; route it to status, sessions, bugs, or another durable owner.
- Preserve user-authored tasks and unrelated instruction/configuration content.
- At closeout, update only facts changed during the session and validate the result.

## Commands

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
project-standards agent-handoff legacy-report --repo . --json
project-standards agent-handoff upgrade --repo . --dry-run --json
```

Automatic profiles support `claude-code` and `codex`; manual mode supports other agents without claiming automatic injection.
