# GitHub Workflow 1.0 summary

The canonical [README](README.md) is authoritative and wins if this summary conflicts with it.

- Package version: `1.0`; applies only to repositories owned by a GitHub organization.
- Configuration is exactly two required options: `organization` (nonempty string) and `harnesses` (nonempty array of `claude-code` or `codex`). Unknown options and empty values are rejected.
- The package is organization-agnostic; `organization` is the only place a consumer names its own organization.
- An issue is the authorized work contract, its organization-level fields carry the typed operational metadata, and a pull request is the execution evidence.
- Load the packaged skill before creating or mutating GitHub work state, and follow its procedures rather than improvising.
- Organization schema — issue types and issue fields — is human-applied. Report differences against the versioned baseline; never mutate organization schema.
- Whether a change needs a pull request is repository-local branch policy this package does not set. Once a pull request exists, its content standard applies.
- Never manipulate rulesets, branch protection, or merge gating: the package must not control the mechanisms judging work performed under it.
- GitHub access uses the operator's existing `gh` authentication. The package embeds no credentials.
- Only the package's bounded managed block in an agent-instruction file is package-owned; the surrounding content stays consumer-owned.
- Reconciliation is offline, deterministic, and convergent on rerun. Hand-edited managed artifacts are reported as drift.
