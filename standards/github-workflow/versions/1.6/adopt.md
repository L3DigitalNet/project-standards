# Adopt GitHub Workflow 1.6

Use this package in an organization-owned repository whose work is tracked as GitHub issues and pull requests, and whose agent sessions should follow one shared discipline when they touch that work state.

The common V5 control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`. This guide covers github-workflow-specific choices only.

## Prerequisites

- The repository is owned by a GitHub organization. A personal-account repository cannot adopt this package: organization-level issue fields do not exist there, and no fallback mode is offered.
- The organization's issue types and issue fields already exist, or a human will apply them. The package reports schema differences; it never creates or edits organization schema.
- The `gh` CLI is installed and already authenticated as the operator. The package embeds no credentials and performs GitHub reads under that existing authentication.
- Agent sessions run on linux/amd64. Version 1.6 ships the `gh-workflow` binary for that platform only. Elsewhere the skill and references still deliver, but every subcommand is unavailable until a payload version carrying that platform exists — reconcile cannot substitute one.

## Select the configuration

Both options are required, so there is no minimal variant that omits either one.

```toml
[standards.github-workflow]
enabled = true
version = "1.6"

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

Every skill file lands twice, under `.agents/skills/github-workflow/` and under `.claude/skills/github-workflow/`, because Claude Code discovers project skills only under the latter and Codex uses the former. Both trees are package-managed and byte-identical; commit both. Editing either is drift.

## First run

Two commands confirm the package works end to end against your organization. Neither writes anything, to GitHub or to your repository:

```bash
.agents/skills/github-workflow/bin/gh-workflow audit     # organization schema, read-only
.agents/skills/github-workflow/bin/gh-workflow summary   # open work, read-only, printed
```

`audit` is read-only in both directions: it compares your live organization schema to the packaged baseline and prints the result, writing nothing. Differences are expected on first adoption and are a report for a human, not a task for an agent — the package never creates, renames, or retires an Issue Type, field, or value.

`summary` prints the attention-first operator summary to stdout and writes no file.

### Upgrading from 1.4 or earlier: the orphaned ledger

Versions 1.0 through 1.4 carried a `ledger` subcommand that generated `docs/GH-WORKFLOWS.md` in your repository. It is removed in 1.5, and nothing regenerates that file any more. It was never a payload artifact — no digest, outside drift-check — so reconcile will neither update nor remove it, and the `upgrade` provider reports it rather than deleting consumer content on your behalf. **Delete `docs/GH-WORKFLOWS.md` yourself** if you committed it, or drop the `.gitignore` entry if you did not; leaving it in place leaves a stale snapshot no tool owns. Also drop any tooling exclusion you added for the path (for example a `markdown-frontmatter` `exclude` entry).

## Committing the shipped binary past an added-file size guard

The `gh-workflow` binary is roughly 9.7 MB and is delivered to both skill trees, so a repository running `pre-commit`'s `check-added-large-files` at a typical `--maxkb=1024` refuses the adoption commit twice over:

```text
.agents/skills/github-workflow/bin/gh-workflow (9695 KB) exceeds 1024 KB.
.claude/skills/github-workflow/bin/gh-workflow (9695 KB) exceeds 1024 KB.
```

Exempt those two paths and leave the threshold alone. Add an `exclude` to the hook entry already in your `.pre-commit-config.yaml`, keeping its existing `repo`, `rev`, and `args`. `exclude` is a regular expression matched against the file path, so anchor it to the exact managed locations rather than to a directory or an extension:

```yaml
- id: check-added-large-files
  args: [--maxkb=1024]
  exclude: ^\.(agents|claude)/skills/github-workflow/bin/gh-workflow$
```

If another package already exempts a binary of its own, combine the alternatives in one anchored expression instead of widening either — for example `^\.(agents/(skills/github-workflow/bin/gh-workflow|hooks/agent-handoff/session-start)|claude/skills/github-workflow/bin/gh-workflow)$`.

Two things this deliberately does not do. It does not raise `--maxkb`, which would stop the guard from noticing an unrelated large file anywhere in the repository — the exact protection the guard exists to give. It does not pass `--no-verify` or disable the hook for the adoption commit, which suspends every hook rather than the one that fired.

Understand what the exemption costs before relying on it. The path stops being size-checked on every future commit, not just this one, so anything that later appears at that path is unmeasured. That is acceptable here because the bytes are not consumer-authored: both copies are `policy = "managed"` artifacts with a digest pinned in the payload, and the control plane re-verifies them. Pair the exemption with the managed-state check at the same boundary so the path the size guard stops watching is still watched:

```bash
project-standards reconcile --check
```

## Living with the package

- Keep configuration changes in `.standards/config.toml` and reapply through reconcile. Editing managed artifacts by hand is reported as drift.
- Content outside the package's managed block in your agent-instruction files remains yours. Reconcile rewrites the block, not the file around it.
- Upgrades arrive as new package versions selected through the catalog. Version 1.6 is immutable once released.
