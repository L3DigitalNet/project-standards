# Adopt the Agent Handoff Standard

The current consumer package is [`agent-handoff@1.14`](versions/1.14/adopt.md). Use it for repository-local project knowledge, manual or automatic session startup, bounded harness integrations, and centrally locked standard-owned runtime artifacts. Consumer-authored `docs/**` knowledge remains create-only.

## Configure and reconcile

Enable the package, then set `contract_version`, `startup`, and `harnesses` under `[standards.agent-handoff.config]`. Manual startup requires an empty harness list; automatic startup accepts `claude-code`, `codex`, or both.

```bash
project-standards standards enable agent-handoff --version 1.14
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

Unsafe paths, duplicate hooks, malformed markers, provenance drift, and size-cap violations fail closed. Restore or reconcile standard-owned bytes; route oversized consumer knowledge by lifetime. See the [version-specific guide](versions/1.14/adopt.md) for exact options, outputs, provider-backed scaffold/upgrade behavior, harness trust, disable semantics, and troubleshooting.

Before enabling the package, take the read-only inventory:

```bash
project-standards agent-handoff legacy-report --repo .
```

It answers before `agent-handoff` appears in `.standards/config.toml`, resolving the installed catalog's default payload and disclosing that basis on stderr, so the evidence that adoption is safe arrives before the selection is committed. The other subcommands still require the selection.

## Excluding paths and the shipped launcher

Where Markdown Tooling is also enabled, declare exclusions through its typed `exclusions` option rather than hand-written `.prettierignore` and `.markdownlint-cli2.jsonc` entries: one `{glob, applies_to, reason}` record covers Prettier and markdownlint together, reaches the managed instruction block, both rendered check commands, and the managed CI callers from a single declaration. Hand-written ignore files remain correct only for repositories that configure those tools independently.

The compiled SessionStart launcher is roughly 3,815 KiB, so a `pre-commit` `check-added-large-files` guard at a typical `--maxkb=1024` refuses the adoption commit. Exempt that one managed path with an anchored `exclude` on the hook entry; raising the repository-wide `--maxkb` or committing with `--no-verify` are both worse trades. The [version-specific guide](versions/1.14/adopt.md) gives the exact expression and what the narrow exemption costs.

Versions 1.1 through 1.7 register the launcher as a bare path whose `#!/usr/bin/env python3` shebang resolves whatever interpreter is first on `PATH`. Where that is a policy shim, a missing interpreter, or one below 3.14, SessionStart injects nothing while every managed byte still matches; `validate` and `drift-check` report `AH-LAUNCHER-INTERPRETER` and direct an upgrade to 1.10 or newer, which has no interpreter prerequisite. Never edit the managed hook or its registration to work around it — both are centrally locked.

## Secret scanners and the managed policy.toml

Reconciliation writes `.standards/packages/agent-handoff/policy.toml`, whose `[credentials].private_key_headers` list contains the literal PEM header strings the package's own credential checker searches for (`-----BEGIN PRIVATE KEY-----` and similar). Gitleaks' default `private-key` rule matches across that array and fails the adoption commit even though no key material exists — the file declares detection patterns, not a credential.

The file is a centrally locked managed artifact, so it cannot carry an inline `gitleaks:allow` comment without creating drift against the lock. Scope the exception to the one rule and the one path rather than allowlisting the path globally:

```toml
[extend]
useDefault = true

[[allowlists]]
description = "Agent Handoff managed policy declares private-key header patterns, not keys"
targetRules = ["private-key"]
paths = ['''^\.standards/packages/agent-handoff/policy\.toml$''']
```

`targetRules` requires Gitleaks v8.25.0 or newer. Narrow it further by AND-ing the path with the header lines themselves (`condition = "AND"` plus `regexTarget = "line"` and a `regexes` entry), and confirm the result with a `gitleaks detect` run before relying on it: the `private-key` match spans several lines, so which line a regex condition sees is worth verifying rather than assuming.

Be clear about what the exception costs. A `paths` allowlist suppresses its rules for that file on **every** commit, so future content at that path stops being scanned by them; without `targetRules` that means _all_ rules, not just `private-key`. Reconciliation's digest verification does not close that gap — it is a separate control that runs later, not a guarantee at commit time. Pair the allowlist with the managed-state check at the same boundary the scanner runs:

```bash
project-standards reconcile --check
```

Run that in pre-commit or CI and any tampering with the managed file fails there, so the path the scanner stops watching is still watched. A per-commit `.gitleaksignore` fingerprint is not a durable alternative: it embeds the commit SHA, so it stops applying the next time reconciliation re-renders the file (a package upgrade or an option change).
