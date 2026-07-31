# Adopt Agent Handoff 1.7

Agent Handoff 1.7 is reconciled by the V5 control plane. Do not copy templates, merge legacy fragments, or retain `.agents/agent-handoff/manifest.json` as a second ownership authority.

## Suitability

Use this package when project knowledge and session continuity must remain repository-local. It supports manual startup, Claude Code, Codex, or both harnesses. It never changes user-global trust, hooks, skills, or credentials.

For automatic startup, verify that the consumer's shebang-resolved `python3` is Python 3.14 or newer. The hook source is payload data with mode `100644`; reconciliation installs the managed artifact with its declared mode `0755`.

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

`contract_version = "1.0"` remains supported independently from the selected 1.7 package for migrated consumers.

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
extend-exclude = [".agents/hooks/agent-handoff/session_start.py"]

[tool.basedpyright]
exclude = [".agents/hooks/agent-handoff/session_start.py"]
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

The skill tree exclusion covers both `.agents/skills/agent-handoff/SKILL.md` and `.agents/skills/agent-handoff/agents/openai.yaml`. The hook exclusion covers `.agents/hooks/agent-handoff/session_start.py`. Exclusions may remain when automatic startup is disabled; an absent path matches no file.

### Secret scanners and the managed policy.toml

Reconciliation writes `.standards/packages/agent-handoff/policy.toml`, whose `[credentials].private_key_headers` list contains the literal PEM header strings this package's own credential checker searches for (`-----BEGIN PRIVATE KEY-----` and similar). A consumer running Gitleaks with default rules will match those strings as the `private-key` rule and fail the adoption commit even though no key material exists — the file is lock-managed, digest-verified content, not a leaked credential.

The file is a centrally locked managed artifact, so it cannot carry an inline `gitleaks:allow` comment without creating drift against the lock. A durable fix is a path allowlist in the consumer's own `.gitleaks.toml`:

```toml
[extend]
useDefault = true

[allowlist]
description = "Agent Handoff managed policy declares private-key header patterns, not keys"
paths = ['''^\.standards/packages/agent-handoff/policy\.toml$''']
```

This is safe because the file's bytes are verified against `.standards/lock.toml` on every reconcile, so allowlisting the path does not create an unwatched hiding place for a real secret. A per-commit `.gitleaksignore` fingerprint is not a durable alternative: it embeds the commit SHA, so it stops applying the next time reconciliation re-renders the file (a package upgrade or an option change).

## Verify

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
git diff --check
git status --short
```

Claude Code and Codex still apply their normal project trust and hook-review workflows. Review the repository-local hook before trusting it.

`AH-SECRET-LITERAL` reports one finding per offending line and names that line, so the message points at the assignment instead of the whole document. Shell command substitution — `TOKEN=$(...)` and its backtick equivalent — is runtime acquisition, not stored material, and is not reported; a credential reference wrapped in a Markdown code span is read as the reference it wraps. A blocked label assigned a literal value, an inline private-key header, and an access-key pattern all still fail closed.

## Authoring operations

`scaffold` creates one missing knowledge document from an immutable package template. `upgrade` refreshes one explicitly authorized standard-owned skill or hook. Both return typed plans; the shared authoring executor performs every write after rechecking the target precondition. Validation, drift, and extraction providers are read-only.

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
