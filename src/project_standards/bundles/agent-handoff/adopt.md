# Adopt the Agent Handoff Standard

Use the released `project-standards` CLI so adoption works without a source checkout.

## Choose a startup mode

Automatic mode requires one or both supported harnesses:

```bash
project-standards adopt agent-handoff --dest . --harness claude-code --harness codex --dry-run
```

Manual mode declares no automatic profile and installs no hook:

```bash
project-standards adopt agent-handoff --dest . --manual --dry-run
```

Review the preview, rerun without `--dry-run`, then validate. Automatic hooks still require the selected harness's normal project trust or approval; this standard never changes global trust settings.

## What adoption changes

Adoption creates missing knowledge templates under `docs/` without replacing existing knowledge. It installs managed skill and hook resources, adds the `agent_handoff` config namespace, updates only the bounded instruction block for selected profiles, and owns only its semantic Claude or bounded Codex hook registration.

All filesystem access stays inside `--dest`. Any unsafe path, symlink escape, malformed config, ambiguous marker, duplicate registration, or unexpected managed drift blocks mutation.

## Validate and maintain

```bash
project-standards agent-handoff validate --repository .
project-standards agent-handoff drift-check --repository .
project-standards agent-handoff size-report --repository .
project-standards agent-handoff shape-check --repository .
```

Use `legacy-report` before migrating an older layout. Reconcile knowledge manually with [`resources/legacy-migration.md`](resources/legacy-migration.md); validate before deleting obsolete repo-local files.

Preview a future managed-artifact refresh before applying it:

```bash
project-standards agent-handoff upgrade --repository . --dry-run
```

Upgrades preserve all create-only knowledge and unrelated configuration. Resolve ambiguous managed drift manually before applying an upgrade.

Exit codes are `0` for success or clean conformance, `1` for findings or a recoverable apply failure, `2` for usage or configuration errors, and `3` for package prerequisites or internal failures.
