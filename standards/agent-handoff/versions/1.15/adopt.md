# Adopt Agent Handoff 1.15

Agent Handoff 1.15 is reconciled by the V5 control plane. Do not copy templates, merge legacy fragments, or retain `.agents/agent-handoff/manifest.json` as a second ownership authority.

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

`contract_version = "1.0"` remains supported independently from the selected 1.15 package for migrated consumers.

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

When Project Standards Markdown Tooling is also enabled, prefer its typed `exclusions` option over hand-written ignore files. Each record takes exactly one `glob` and covers Prettier and markdownlint together, carrying its own justification — so the two installed skill trees need one record each:

```toml
[[standards.markdown-tooling.config.exclusions]]
glob = ".agents/skills/agent-handoff/**"
applies_to = "both"
reason = "Centrally locked Agent Handoff skill tree; editing it to satisfy a formatter creates drift."

[[standards.markdown-tooling.config.exclusions]]
glob = ".claude/skills/agent-handoff/**"
applies_to = "both"
reason = "Centrally locked Agent Handoff skill tree for Claude Code; editing it to satisfy a formatter creates drift."
```

Reconciling that renders the exclusion into the managed `markdown-tooling` instruction block, into both rendered check commands as a `:(glob,exclude)` pathspec, and into the managed CI callers — all from the same declaration, so the three cannot drift apart. Hand-written ignore files reach none of those surfaces, and `.markdownlint-cli2.jsonc` is specifically the runner-config class whose `globs` key Markdown Tooling's rendered `--no-globs` exists to neutralize.

The two instructions below are for repositories that configure Prettier or markdownlint-cli2 independently of Markdown Tooling.

For Prettier, add the locked skill tree to `.prettierignore`:

```gitignore
.agents/skills/agent-handoff/**
.claude/skills/agent-handoff/**
```

For markdownlint-cli2, preserve existing settings and add the same tree to `ignores` in `.markdownlint-cli2.jsonc`:

```json
{ "ignores": [".agents/skills/agent-handoff/**", ".claude/skills/agent-handoff/**"] }
```

The skill tree exclusions cover `SKILL.md` and `agents/openai.yaml` under both installed trees — `.agents/skills/agent-handoff/` and `.claude/skills/agent-handoff/`. The hook exclusion covers `.agents/hooks/agent-handoff/session-start`. Exclusions may remain when automatic startup is disabled; an absent path matches no file.

### Added-file size guards and the compiled launcher

The managed launcher is a statically linked executable of roughly 3,815 KiB, so a `pre-commit` `check-added-large-files` guard — commonly `--maxkb=1024` — rejects the adoption commit:

```text
.agents/hooks/agent-handoff/session-start (3815 KB) exceeds 1024 KB.
```

Exempt that one path and leave the repository-wide threshold where it is:

```yaml
- id: check-added-large-files
  args: [--maxkb=1024]
  exclude: ^\.agents/hooks/agent-handoff/session-start$
```

Do not raise the global `--maxkb` and do not commit with the hooks skipped. Both trade a guard that protects every other file in the repository for one known, reviewed, centrally locked artifact. `exclude` takes a single anchored regular expression, so a repository that must exempt more than one binary lists them as alternates — `^(\.agents/hooks/agent-handoff/session-start|<other path>)$` — rather than relaxing the limit.

The path is exact and stable: reconciliation installs the launcher only at that target, and only when automatic startup is selected. Manual startup installs no launcher and needs no exemption.

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

## Upgrade from 1.14

1.15 is a gating-only cut: the `openai.yaml` skill sidecar is a Codex descriptor, so it now installs solely at `.agents/skills/agent-handoff/agents/openai.yaml`, gated on `harnesses` containing `codex`. The `.claude/skills/agent-handoff/agents/openai.yaml` copy no longer exists as a declared artifact; a Claude-only consumer (`harnesses = ["claude-code"]`) sees it removed on reconcile. No other option, policy value, template, hook, provider, contribution, or artifact target changes.

## Upgrade from 1.13

1.14 changed the packaged skill text only. The closeout procedure now names the numeric document caps it previously left implicit, opens with a `delta` survey of the session, and runs closeout validation with `--since` so a fresh finding is not buried under pre-existing advisory warnings on append-only documents. No option, policy value, template, hook, provider, contribution, or artifact target changes; reconciling 1.14 rewrote the two installed `SKILL.md` copies and nothing else.

Both skill trees are managed and byte-identical, so the refresh lands in `.agents/skills/agent-handoff/SKILL.md` and `.claude/skills/agent-handoff/SKILL.md` together. Commit them.

## Upgrade from 1.9 or earlier

Reconciliation installs the compiled launcher at `.agents/hooks/agent-handoff/session-start` and rewrites both harness registrations to invoke it. Nothing else in the contract changes: the emitted SessionStart context is byte-identical to 1.9's.

In a clean V5-native repository, reconciliation removes the unchanged superseded `.agents/hooks/agent-handoff/session_start.py` when the selected package no longer declares it. Consumer-modified bytes fail closed with `CP-MODIFIED-MANAGED`; review the reported drift instead of deleting the path by hand.

After a clean reconciliation, drop that path from any formatter or linter exclusion the 1.9 adoption added, and add the new one — see the exclusions above.

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
