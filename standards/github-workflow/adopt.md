# Adopt the GitHub Workflow Standard

The current consumer package is [`github-workflow@1.7`](versions/1.7/adopt.md). Use it in a repository owned by a GitHub organization whose work is tracked as issues and pull requests: it delivers the repo-local agent skill, its references, and the `gh-workflow` binary into both `.agents/skills/github-workflow/` and `.claude/skills/github-workflow/`, plus one managed instruction block per selected harness.

It does not apply to personal-account repositories. Organization-level issue fields do not exist outside an organization, and the package offers no fallback that operates without them.

## Configure and reconcile

Both options are required, so there is no minimal variant that omits either one. Set `organization` to the login of the organization that owns the repository, and list in `harnesses` only the harnesses the repository actually uses.

```bash
project-standards standards enable github-workflow --version 1.7
project-standards reconcile
project-standards reconcile --apply
```

Reconciliation is offline and deterministic; rerunning it converges rather than accumulating changes. It delivers the skill, its six references, the `gh-workflow` binary, the rendered `.standards/packages/github-workflow/policy.toml`, and — per selected harness — the managed instruction block and the Codex companion.

## Verify and troubleshoot

```bash
project-standards reconcile --check
.agents/skills/github-workflow/bin/gh-workflow audit
```

`audit` is read-only: it compares live organization schema against the packaged baseline and prints the result. Differences are expected on first adoption and are a report for a human — the package never creates, renames, or retires an Issue Type, field, or value.

Every subcommand is read-only against the repository; nothing this package ships writes a file into the checkout. Versions 1.0 through 1.4 carried a `ledger` subcommand that generated `docs/GH-WORKFLOWS.md`; 1.5 removes it, and a repository upgrading from an earlier version deletes that now-unowned file itself. See the [version-specific guide](versions/1.7/adopt.md) for exact options, first-run expectations, and troubleshooting.

Agent sessions run the binary on linux/amd64. Elsewhere the skill and references still deliver, but every subcommand is unavailable until a payload version carrying that platform exists; reconcile cannot substitute one.

## Added-file size guards and the shipped binary

The `gh-workflow` binary is roughly 9.7 MB and is delivered to both skill trees, so a repository running `pre-commit`'s `check-added-large-files` at a typical `--maxkb=1024` refuses the adoption commit twice over:

```text
.agents/skills/github-workflow/bin/gh-workflow (9695 KB) exceeds 1024 KB.
.claude/skills/github-workflow/bin/gh-workflow (9695 KB) exceeds 1024 KB.
```

Exempt those two paths and leave the repository-wide threshold where it is. Add an `exclude` to the hook entry already in `.pre-commit-config.yaml`, anchored to the exact managed locations rather than to a directory or an extension:

```yaml
- id: check-added-large-files
  args: [--maxkb=1024]
  exclude: ^\.(agents|claude)/skills/github-workflow/bin/gh-workflow$
```

Where another package also ships a managed binary, combine the alternatives in one anchored expression instead of widening either.

Raising `--maxkb` and bypassing hooks with `--no-verify` are both worse trades: the first stops the guard noticing an unrelated large file anywhere in the repository, and the second suspends every hook rather than the one that fired. The narrow exemption still costs something — the path stops being size-checked on every future commit — which is acceptable only because the bytes are `policy = "managed"` artifacts with a digest pinned in the payload. Pair it with the managed-state check at the same boundary so the path the size guard stops watching is still watched:

```bash
project-standards reconcile --check
```
