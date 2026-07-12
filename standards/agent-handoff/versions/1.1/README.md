# Agent Handoff Standard

Agent Handoff package `1.1` defines repository-local project knowledge, bounded session continuity, and deterministic conformance checks for coding agents. The package supports consumer contracts `1.0` and `1.1` independently from its payload version. An adopting repository is the complete authority boundary: the standard never requires a separate checkout and never creates, reads, or stores consumer state outside that repository.

## Goals and boundaries

Agent Handoff provides:

- a canonical project-knowledge layout under `docs/`;
- a repo-local `agent-handoff` skill shared by supported agents;
- optional automatic SessionStart context for Claude Code and Codex;
- create-only knowledge scaffolds and refreshable standard-owned runtime files;
- bounded instruction and harness configuration integration;
- size, shape, drift, credential-reference, and legacy-evidence checks.

It does not own workstation configuration, global skills or hooks, sibling repositories, credentials, fleet rollout, or consumer-authored knowledge after creation.

## Ownership model

| Surface | Owner | Lifecycle |
| --- | --- | --- |
| `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/**` | Consumer | Created only when missing; never overwritten by adoption, repair, drift checking, or upgrade |
| `.agents/skills/agent-handoff/**` | Standard | Installed and hash-tracked |
| `.agents/hooks/agent-handoff/session_start.py` | Standard | Installed only for automatic mode; executable and hash-tracked |
| Managed blocks in selected `AGENTS.md` or `CLAUDE.md` surfaces | Standard inside markers; consumer outside | Structurally merged; outside bytes are preserved |
| Agent Handoff entry in `.claude/settings.json` | Standard entry; consumer surrounding object | Semantically merged |
| Agent Handoff entry in `.codex/config.toml` | Standard array-table entry; consumer surrounding tables and entries | Semantically merged by matcher identity |
| `.standards/packages/agent-handoff/policy.toml` | Standard | Non-discovered package-local provider policy; centrally hash-tracked |
| `.standards/lock.toml` entries | Control plane | Sole generic inventory for applied Agent Handoff artifacts and semantic units |

Ambiguous markers, duplicate registrations, symlinked paths, invalid configuration, and unverified managed drift fail closed before mutation.

## Canonical knowledge layout

```text
docs/
├── STATUS.md
├── TODO.md
└── handoff/
    ├── state.md
    ├── deployed.md
    ├── architecture.md
    ├── credentials.md
    ├── conventions.md
    ├── specs-plans.md
    ├── sessions/
    └── bugs/
```

| Path | Purpose |
| --- | --- |
| `docs/STATUS.md` | Small current project snapshot, not a changelog |
| `docs/TODO.md` | User-owned and agent-owned work queues |
| `docs/handoff/state.md` | Next-session focus and active incidents only |
| `docs/handoff/deployed.md` | Current deployment truth |
| `docs/handoff/architecture.md` | Stable structure, boundaries, and standing structural backlog |
| `docs/handoff/credentials.md` | Environment-variable names, secret names, OpenBao paths, and retrieval instructions—never values |
| `docs/handoff/conventions.md` | Stable project-specific patterns |
| `docs/handoff/specs-plans.md` | Pointers to active specifications and plans |
| `docs/handoff/sessions/` | Append-only compact session history |
| `docs/handoff/bugs/` | Stable numbered bug, gotcha, cause, fix, and lesson records |

Facts move out of eager state when they are completed, no longer active, or have a durable owner. History belongs in session or bug records, not in `state.md` or the current status snapshot.

## Startup profiles

| Profile | Configuration | Startup behavior |
| --- | --- | --- |
| Manual | `startup: manual`, no harnesses | The agent follows the repo-local skill, reads `state.md`, and inspects Git state |
| Claude Code | `startup: automatic`, `claude-code` | Project `SessionStart` command emits JSON `additionalContext` |
| Codex | `startup: automatic`, `codex` | Trusted project `SessionStart` command emits plain stdout context |
| Dual | Both harnesses | Both registrations invoke the same shared repo-local hook |

The control plane owns one bounded unit per selected harness. Unselected hooks, instructions, and harness entries are absent; changing profiles removes only previously locked units and preserves unrelated surrounding configuration.

Automatic profiles require the selected harness's normal project trust and hook review. Agent Handoff documents that prerequisite but never changes user or global trust state.

The hook derives repository authority from its installed path. Event `cwd` and environment variables are metadata, not filesystem authority. It reads only canonical `docs/handoff/state.md`, uses fixed Git argument arrays with timeouts, and degrades to explicit unavailable markers when Git or documents cannot be read.

## Context and document budgets

- `docs/handoff/state.md`: hard cap 2,048 UTF-8 bytes; target 1,740 bytes.
- Total Claude or Codex SessionStart output: hard cap 4,096 UTF-8 bytes.
- Git context: five commits and ten working-tree lines.
- `CLAUDE.md`: target 1,740 bytes; advisory cap 2,048 bytes.
- `AGENTS.md`: target 3,480 bytes; advisory cap 4,096 bytes.

Repository-derived content is wrapped as untrusted reference data. Literal `session_context` tags are neutralized before wrapping, and the inner content is clamped before the closing boundary is added.

## Skill and closeout contract

Reconciliation installs `.agents/skills/agent-handoff/SKILL.md`. Agents use it at startup, when routing a durable fact, whenever handoff files are edited, and at session closeout.

Closeout updates only facts changed during the session:

1. move current outcomes to `docs/STATUS.md`;
2. preserve the user task section and update the agent queue in `docs/TODO.md`;
3. keep only active work and incidents in `docs/handoff/state.md`;
4. route stable facts to the matching lazy document;
5. append a compact session record or durable bug lesson when useful;
6. run relevant validation and review the diff.

## Credentials and repository safety

Credential values are forbidden. References such as `OPENBAO_ADDR`, `bao://kv/project/path`, and `secret/data/project` are allowed. Private-key headers, high-confidence access-key forms, and literal credential assignments fail validation without echoing matched values.

All planned consumer paths are validated before writes. Reconciliation and typed authoring use atomic publication, recheck content hashes immediately before replacement, preserve create-only knowledge even when managed writes are enabled, and publish the central lock last.

## Conformance and maintenance

Use the released package CLI:

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
```

A conforming repository has the required knowledge layout, closed package configuration, selected-profile bounded integrations, current standard-owned artifacts, a valid central lock, reference-only credentials, and no fatal policy findings.

See [`adopt.md`](adopt.md) for installation and maintenance. Use [`resources/legacy-migration.md`](resources/legacy-migration.md) for agent-guided migration from older layouts.
