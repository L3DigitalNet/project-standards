# Adopt the Agent Handoff Standard

The current consumer package is [`agent-handoff@1.6`](versions/1.6/adopt.md). Use it for repository-local project knowledge, manual or automatic session startup, bounded harness integrations, and centrally locked standard-owned runtime artifacts. Consumer-authored `docs/**` knowledge remains create-only.

## Configure and reconcile

Enable the package, then set `contract_version`, `startup`, and `harnesses` under `[standards.agent-handoff.config]`. Manual startup requires an empty harness list; automatic startup accepts `claude-code`, `codex`, or both.

```bash
project-standards standards enable agent-handoff --version 1.6
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

Unsafe paths, duplicate hooks, malformed markers, provenance drift, and size-cap violations fail closed. Restore or reconcile standard-owned bytes; route oversized consumer knowledge by lifetime. See the [version-specific guide](versions/1.6/adopt.md) for exact options, outputs, provider-backed scaffold/upgrade behavior, harness trust, disable semantics, and troubleshooting.

## Secret scanners and the managed policy.toml

Reconciliation writes `.standards/packages/agent-handoff/policy.toml`, whose `[credentials].private_key_headers` list contains the literal PEM header strings the package's own credential checker searches for (`-----BEGIN PRIVATE KEY-----` and similar). A consumer running Gitleaks with default rules will match those strings as the `private-key` rule and fail the adoption commit even though no key material exists — the file is lock-managed, digest-verified content, not a leaked credential.

The file is a centrally locked managed artifact, so it cannot carry an inline `gitleaks:allow` comment without creating drift against the lock. A durable fix is a path allowlist in the consumer's own `.gitleaks.toml`:

```toml
[extend]
useDefault = true

[allowlist]
description = "Agent Handoff managed policy declares private-key header patterns, not keys"
paths = ['''^\.standards/packages/agent-handoff/policy\.toml$''']
```

This is safe because the file's bytes are verified against `.standards/lock.toml` on every reconcile, so allowlisting the path does not create an unwatched hiding place for a real secret. A per-commit `.gitleaksignore` fingerprint is not a durable alternative: it embeds the commit SHA, so it stops applying the next time reconciliation re-renders the file (a package upgrade or an option change).
