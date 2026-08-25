# GitHub Workflow 1.4 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.4`; applies only to repositories owned by a GitHub organization.
- Configuration is exactly two required options: `organization` (nonempty string) and `harnesses` (nonempty array of `claude-code` or `codex`). Unknown options and empty values are rejected.
- The package is organization-agnostic; `organization` is the only place a consumer names its own organization.
- Adoption: set both options in `.standards/config.toml`, then `project-standards reconcile` and `project-standards validate`.
- Reconcile delivers the skill, six references, and the `gh-workflow` binary under both `.agents/skills/github-workflow/` and `.claude/skills/github-workflow/`, renders `.standards/packages/github-workflow/policy.toml`, and adds one managed instruction block per selected harness.
- The two skill trees are byte-identical managed copies from one source: Claude Code discovers project skills only under `.claude/skills/`, Codex only under `.agents/skills/`. Never edit or delete one to deduplicate them.
- `ledger` writes a repository file and `audit` does not; treat a first run of `ledger` as a reviewable repository change.
- `gh-workflow` is a static linux/amd64 binary with nine subcommands — `audit`, `ledger`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check`. Route mechanical actions through them instead of improvising raw `gh` mutations.
- `docs/GH-WORKFLOWS.md` is tool-generated: owned whole-file by `ledger`, outside the payload digests and drift-check, never hand-edited. Its body depends on work state alone, so regenerating unchanged state produces no diff; `ledger` prints the read time to stdout.
- An issue is the authorized work contract, its organization-level fields carry the typed operational metadata, and a pull request is the execution evidence.
- Load the packaged skill before creating or mutating GitHub work state, and follow its procedures rather than improvising.
- Organization schema — issue types and issue fields — is human-applied. Report differences against the versioned baseline; never mutate organization schema.
- Whether a change needs a pull request is repository-local branch policy this package does not set. Once a pull request exists, its content standard applies.
- Never manipulate rulesets, branch protection, or merge gating: the package must not control the mechanisms judging work performed under it.
- GitHub access uses the operator's existing `gh` authentication. The package embeds no credentials.
- Only the package's bounded managed block in an agent-instruction file is package-owned; the surrounding content stays consumer-owned.
- Reconciliation is offline, deterministic, and convergent on rerun. Hand-edited managed artifacts are reported as drift.
