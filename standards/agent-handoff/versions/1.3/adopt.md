# Adopt Agent Handoff 1.3

Agent Handoff 1.3 is reconciled by the V5 control plane. Do not copy templates, merge legacy fragments, or retain `.agents/agent-handoff/manifest.json` as a second ownership authority.

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

`contract_version = "1.0"` remains supported independently from the selected 1.3 package for migrated consumers.

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

## Verify

```bash
project-standards agent-handoff validate --repo .
project-standards agent-handoff drift-check --repo .
git diff --check
git status --short
```

Claude Code and Codex still apply their normal project trust and hook-review workflows. Review the repository-local hook before trusting it.

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
