# Adopt the Agent Handoff Standard

Adopt Agent Handoff from a released `project-standards` installation. No source checkout is required.

## Prerequisites

- Run commands from the repository being adopted or pass its path with `--dest` or `--repo`.
- Review uncommitted changes that overlap `docs/`, `.agents/`, `.claude/`, `.codex/`, `AGENTS.md`, `CLAUDE.md`, or `.project-standards.yml`.
- Choose exactly one startup mode.
- For automatic mode, confirm Python 3 and Git are available to the repository-local hook.

## Preview adoption

Manual mode supports any agent and registers no automatic hook:

```bash
project-standards adopt agent-handoff \
  --dest . \
  --manual \
  --dry-run \
  --json
```

Automatic mode requires one or both supported harnesses:

```bash
project-standards adopt agent-handoff \
  --dest . \
  --harness claude-code \
  --harness codex \
  --dry-run \
  --json
```

The preview is the complete aggregate plan. Another standard may share the same invocation:

```bash
project-standards adopt agent-handoff markdown-tooling \
  --dest . \
  --manual \
  --dry-run \
  --json
```

Review every create, update, skip, blocker, and finding. A blocked preflight writes nothing.

## Apply and inspect

Rerun the reviewed command without `--dry-run`. Adoption:

- creates missing consumer knowledge under `docs/` without replacing existing content;
- installs the repo-local skill;
- installs the shared hook only for automatic mode;
- adds the strict `agent_handoff` configuration block;
- adds bounded instructions to the selected harness files;
- semantically merges Claude settings or a bounded Codex TOML block;
- writes the provenance lock only after every preceding action succeeds.

After adoption:

```bash
project-standards agent-handoff validate --repo .
git status --short
git diff --check
git diff
```

## Harness trust and hook review

Claude Code and Codex apply their own project trust and hook-review workflows. Agent Handoff never writes user-global trust state.

For Claude Code, review the project `.claude/settings.json` handler. It invokes:

```text
${CLAUDE_PROJECT_DIR}/.agents/hooks/agent-handoff/session_start.py
```

For Codex, trust the project `.codex/` layer and review the inline `SessionStart` command. A project `.codex/hooks.json` alongside inline hooks is an adoption blocker because Codex loads both sources.

Both harnesses must invoke the same executable at `.agents/hooks/agent-handoff/session_start.py`. On the next startup, confirm context is injected once and ends with `</session_context>`.

## Validate and maintain

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
```

- `validate` accumulates layout, config, integration, artifact, provenance, reference, shape, size, and credential findings.
- `drift-check` limits output to standard-owned artifacts, integrations, and the provenance lock.
- `size-report` reports UTF-8 byte targets and caps.
- `shape-check` reports fatal eager-document rules and advisory lazy-document rules.

Exit codes are:

| Code | Meaning                                   |
| ---- | ----------------------------------------- |
| 0    | Clean conformance or successful operation |
| 1    | Findings or recoverable apply failure     |
| 2    | Usage or consumer configuration error     |
| 3    | Missing or invalid package prerequisite   |

## Upgrade managed artifacts

Preview an upgrade:

```bash
project-standards agent-handoff upgrade --repo . --dry-run --json
```

Apply only after reviewing the plan:

```bash
project-standards agent-handoff upgrade --repo .
```

Upgrade requires a valid provenance lock and matching on-disk hashes for every previously managed entry. Local changes to standard-owned artifacts block the entire upgrade. Consumer knowledge files are create-only and are never compared as overwrite candidates.

## Migrate an older layout

Run the read-only evidence report first:

```bash
project-standards agent-handoff legacy-report --repo . --json
```

Follow [`resources/legacy-migration.md`](resources/legacy-migration.md). The repository's local agent inventories and reconciles facts by lifetime. The package does not perform semantic conversion, scan global state, or delete obsolete files.

## Troubleshooting

| Finding | Safe next action |
| --- | --- |
| Unsafe or symlinked path | Replace it with a reviewed regular repository path; do not follow it automatically |
| Malformed or duplicate markers | Reconcile the owned block manually, then preview again |
| Existing unverified skill or hook | Compare local intent, preserve legitimate changes, and remove or restore it deliberately |
| Claude duplicate or legacy handler | Consolidate to one exact v1 project handler |
| Codex `hooks.json` coexistence | Consolidate project hooks into one reviewed representation |
| Provenance drift | Restore locked content or reconcile the local change before upgrade |
| Hook not trusted | Complete the harness's project trust and hook-review workflow |
| State or output over budget | Route durable detail to lazy files and keep pointers in eager state |
