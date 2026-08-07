# Adopt GitHub Workflow 1.0

Use this package in an organization-owned repository whose work is tracked as GitHub issues and pull requests, and whose agent sessions should follow one shared discipline when they touch that work state.

The common V5 control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`. This guide covers github-workflow-specific choices only.

## Prerequisites

- The repository is owned by a GitHub organization. A personal-account repository cannot adopt this package: organization-level issue fields do not exist there, and no fallback mode is offered.
- The organization's issue types and issue fields already exist, or a human will apply them. The package reports schema differences; it never creates or edits organization schema.
- The `gh` CLI is installed and already authenticated as the operator. The package embeds no credentials and performs GitHub reads under that existing authentication.
- Agent sessions run on linux/amd64. Version 1.0 ships the `gh-workflow` binary for that platform only. Elsewhere the skill and references still deliver, but every subcommand is unavailable until a payload version carrying that platform exists — reconcile cannot substitute one.

## Select the configuration

Both options are required, so there is no minimal variant that omits either one.

```toml
[standards.github-workflow]
enabled = true
version = "1.0"

[standards.github-workflow.config]
organization = "example-org"
harnesses = ["claude-code", "codex"]
```

Set `organization` to the login of the organization that owns the repository. It is the only place an organization name enters the package.

List in `harnesses` only the harnesses the repository actually uses. Each listed harness receives the managed instruction block that points its sessions at the packaged skill; a harness left out receives nothing. Valid entries are `claude-code` and `codex`, and the list must not be empty — an adoption that instructs no harness would install the skill without binding any session to it.

## Apply and verify

Reconcile the repository through `project-standards`, then confirm the result:

```bash
project-standards reconcile
project-standards validate
```

Reconciliation is offline and deterministic. Rerunning it converges rather than accumulating changes, so a repeated run is a safe way to confirm the repository matches the package.

Reconcile delivers the skill, its six references, the `gh-workflow` binary, the rendered policy file, and — for each selected harness — the instruction block and the Codex companion. [`README.md`](README.md#4-what-the-package-delivers) lists the exact paths and their conditions.

## First run

Two commands confirm the package works end to end against your organization, and neither mutates anything:

```bash
.agents/skills/github-workflow/bin/gh-workflow audit
.agents/skills/github-workflow/bin/gh-workflow ledger
```

`audit` compares your live organization schema to the packaged baseline read-only. Differences are expected on first adoption and are a report for a human, not a task for an agent: the package never creates, renames, or retires an Issue Type, field, or value. `ledger` writes `docs/GH-WORKFLOWS.md` from live state — commit it or ignore it, but never hand-edit it; the tool owns that file whole and regenerates it.

## Living with the package

- Keep configuration changes in `.standards/config.toml` and reapply through reconcile. Editing managed artifacts by hand is reported as drift.
- Content outside the package's managed block in your agent-instruction files remains yours. Reconcile rewrites the block, not the file around it.
- Upgrades arrive as new package versions selected through the catalog. Version 1.0 is immutable once released.
