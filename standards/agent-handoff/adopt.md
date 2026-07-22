# Adopt the Agent Handoff Standard

The current consumer package is [`agent-handoff@1.4`](versions/1.4/adopt.md). Use it for repository-local project knowledge, manual or automatic session startup, bounded harness integrations, and centrally locked standard-owned runtime artifacts. Consumer-authored `docs/**` knowledge remains create-only.

## Configure and reconcile

Enable the package, then set `contract_version`, `startup`, and `harnesses` under `[standards.agent-handoff.config]`. Manual startup requires an empty harness list; automatic startup accepts `claude-code`, `codex`, or both.

```bash
project-standards standards enable agent-handoff --version 1.4
project-standards reconcile
project-standards reconcile --apply
```

Reconciliation installs the repo-local skill, optional shared hook, bounded instruction/settings units, and `.standards/packages/agent-handoff/policy.toml`. It records them in the central lock; it does not create a package-specific provenance lock.

## Migrate a V4 repository

```bash
project-standards init --catalog 5 --migrate
project-standards init --catalog 5 --migrate --apply
```

Review exact legacy markers, hook settings, and `.agents/agent-handoff/manifest.json` evidence before apply. Unknown or modified managed bytes block the whole migration. Successful apply preserves consumer knowledge and retires the legacy lock only after unified verification.

## Verify and troubleshoot

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
project-standards agent-handoff size-report --repo .
project-standards agent-handoff shape-check --repo .
```

Unsafe paths, duplicate hooks, malformed markers, provenance drift, and size-cap violations fail closed. Restore or reconcile standard-owned bytes; route oversized consumer knowledge by lifetime. See the [version-specific guide](versions/1.4/adopt.md) for exact options, outputs, provider-backed scaffold/upgrade behavior, harness trust, disable semantics, and troubleshooting.
