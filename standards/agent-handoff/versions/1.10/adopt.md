# Adopt Agent Handoff 1.9

Agent Handoff 1.9 is reconciled by the V5 control plane. Do not copy templates, merge legacy fragments, or retain `.agents/agent-handoff/manifest.json` as a second ownership authority.

## Suitability

Use this package when project knowledge and session continuity must remain repository-local. It supports manual startup, Claude Code, Codex, or both harnesses. It never changes user-global trust, hooks, skills, or credentials.

Automatic startup has no runtime prerequisite: the launcher is a statically linked `linux/amd64` executable shipped as committed payload bytes, and reconciliation installs it with its declared mode `0755`. Select manual startup on any other operating system or architecture.

## Configure

Add the package to `.standards/config.toml`:

```toml
[standards.agent-handoff]
enabled = true
version = "latest"

[standards.agent-handoff.config]
contract_version = "1.1"
startup = "automatic"
harnesses = ["claude-code", "codex"]
```

Manual startup requires an empty harness list:

```toml
[standards.agent-handoff.config]
contract_version = "1.1"
startup = "manual"
harnesses = []
```

`contract_version = "1.0"` remains supported independently from the selected 1.9 package for migrated consumers.

## Preview and apply

```bash
project-standards reconcile --check
project-standards reconcile --apply
```

Reconciliation:

- creates missing `docs/STATUS.md`, `docs/TODO.md`, and `docs/handoff/**` knowledge only once;
- centrally manages the repo-local skill, shared hook, package policy, bounded instruction blocks, and harness settings;
- preserves consumer content outside package units;
- writes `.standards/lock.toml` only after verification.

The policy used by version-selected providers lives at `.standards/packages/agent-handoff/policy.toml`. Unselected harness units are absent. Manual mode installs no hook, and profile changes remove only the package's centrally locked semantic entries.

Instruction-file size reports exclude exact managed Markdown envelopes authenticated by the central lock. Consumer-authored bytes and any ambiguous, malformed, unlocked, or drifted managed-marker lookalikes still count toward the configured budget.

## Exclude locked artifacts from independent tools

Agent Handoff owns the exact managed `.agents/` classes described in the [independent repository tooling boundary](README.md#independent-repository-tooling-boundary). Add exclusions only when independently configured tools would otherwise select them. Do not edit the installed files to satisfy an external formatter, linter, or type checker.

For Ruff and BasedPyright configured in `pyproject.toml`, preserve any existing entries and add the managed hook path:

```toml
[tool.ruff]
extend-exclude = [".agents/hooks/agent-handoff/session-start"]

[tool.basedpyright]
exclude = [".agents/hooks/agent-handoff/session-start"]
```

Project Standards Python Tooling's default Ruff exclusion for `.agents` already covers the hook. Its generated BasedPyright configuration includes only declared source and test roots, so no additional entry is needed unless a consumer broadens that scope independently.

For Prettier, add the locked skill tree to `.prettierignore`:

```gitignore
.agents/skills/agent-handoff/**
```

For markdownlint-cli2, preserve existing settings and add the same tree to `ignores` in `.markdownlint-cli2.jsonc`:

```json
{ "ignores": [".agents/skills/agent-handoff/**"] }
```

The skill tree exclusion covers both `.agents/skills/agent-handoff/SKILL.md` and `.agents/skills/agent-handoff/agents/openai.yaml`. The hook exclusion covers `.agents/hooks/agent-handoff/session-start`. Exclusions may remain when automatic startup is disabled; an absent path matches no file.

### Secret scanners and the managed policy.toml

Reconciliation writes `.standards/packages/agent-handoff/policy.toml`, whose `[credentials].private_key_headers` list contains the literal PEM header strings this package's own credential checker searches for (`-----BEGIN PRIVATE KEY-----` and similar). Gitleaks' default `private-key` rule matches across that array and fails the adoption commit even though no key material exists — the file declares detection patterns, not a credential.

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

## Verify

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
git diff --check
git status --short
```

Claude Code and Codex still apply their normal project trust and hook-review workflows. Review the repository-local hook before trusting it.

If the harness reports that the SessionStart hook could not be executed, confirm that `.agents/hooks/agent-handoff/session-start` exists with mode `0755` and reconcile the package; on a platform the launcher does not target, select manual startup instead.

Upgrading from `1.8` rewrites the managed `.claude/settings.json` unit to drop `args`. That field selects the harness spawn mode, and `1.8` paired an empty array with a shell command line, so its SessionStart hook failed with `ENOENT` and injected no context while every conformance check stayed green. Reconciliation replaces the managed unit in place; it does not add a second handler. After applying, confirm the entry has no `args` key and that a new session injects the `state.md` section.

`AH-SECRET-LITERAL` reports one finding per offending line and names that line, so the message points at the assignment instead of the whole document. `TOKEN=$(...)` is read as runtime acquisition rather than stored material, and its backtick equivalent is too **when the command names its source** — `` TOKEN=`bao kv get -field=value secret/apps/example` `` and `` TOKEN=`credential-helper read env:CRED` `` are accepted because `secret/apps/example` and `env:CRED` each satisfy the reference policy. A backtick command that names no reference is not an acquisition: `` TOKEN=`printf '%s' 'literal'` `` and `` password: `echo literal` `` are a credential written as a command argument and still fail closed. A credential reference wrapped in a Markdown code span is read as the reference it wraps, while a single-token span that names nothing (`` token: `abc123` ``) stays reported. Inline private-key headers and access-key patterns are unchanged.

## Authoring operations

`scaffold` creates one missing knowledge document from an immutable package template. `upgrade` refreshes one explicitly authorized standard-owned skill or hook. Both return typed plans; the shared authoring executor performs every write after rechecking the target precondition. Validation, drift, and extraction providers are read-only.

## Upgrade from 1.9 or earlier

Reconciliation installs the compiled launcher at `.agents/hooks/agent-handoff/session-start` and rewrites both harness registrations to invoke it. Nothing else in the contract changes: the emitted SessionStart context is byte-identical to 1.9's.

One step is manual. The payload contract has no policy for retiring a file an earlier version installed, so reconciliation leaves the superseded `.agents/hooks/agent-handoff/session_start.py` in place and reports it as preserved consumer bytes. No registration references it after the upgrade, so it is inert; delete it once reconciliation reports clean:

```bash
git rm .agents/hooks/agent-handoff/session_start.py
```

Also drop that path from any formatter or linter exclusion the 1.9 adoption added, and add the new one — see the exclusions above.

## Migrate a V4 consumer

Use the unified migration instead of deleting the old lock or markers manually:

```bash
project-standards init --migrate --catalog 5
project-standards init --migrate --catalog 5 --apply
```

Migration preserves the legacy `agent_handoff` contract/startup/harness choices, create-only consumer knowledge, unrelated instruction text, unrelated Claude settings, and unrelated Codex configuration. It recognizes exact legacy instruction, Codex-hook, project-config, and package-lock signatures. Unknown versions, paths, owners, digests, partial markers, or modified managed bytes block the complete migration.

After successful verification, the executor removes `.project-standards.yml` and `.agents/agent-handoff/manifest.json`; the central lock is then the only generic artifact inventory. See [Legacy Handoff Migration](resources/legacy-migration.md) for evidence that still requires human routing.

## Disable or re-enable

Set `enabled = false`, preview, and apply. Standard-owned runtime files, integration units, and package-local policy are removed under central-lock preconditions. Consumer knowledge remains untouched. Re-enabling reconstructs standard-owned units and does not replace existing knowledge.
