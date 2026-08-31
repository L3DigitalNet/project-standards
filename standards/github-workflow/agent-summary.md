# GitHub Workflow family: Agent Summary

Current authority is the Catalog 5 consumer payload [`github-workflow@1.8`](versions/1.8/agent-summary.md). Its [versioned standard](versions/1.8/README.md) and installed repo-local skill win over this mutable navigation summary.

- Load the packaged skill before creating or mutating GitHub work state, and follow its procedures rather than improvising raw `gh` calls.
- An issue is the authorized work contract, its organization-level fields carry the typed operational metadata, and a pull request is the execution evidence.
- Organization schema — issue types and issue fields — is human-applied. Report differences against the versioned baseline; never create, rename, or retire one.
- Route mechanical actions through the `gh-workflow` subcommands: `audit`, `new`, `set`, `close`, `reopen`, `summary`, `receipt`, `check`. The skill's routing table is the complete flag surface and names the raw `gh` forms for what the tool deliberately does not cover.
- Every subcommand reads the consumer's repository and writes none of it: 1.5 removed `ledger` and the `docs/GH-WORKFLOWS.md` it generated. A consumer upgrading from 1.4 deletes that orphaned file itself; the package never removes consumer content.
- From 1.6, not every finding needs an issue: fix a related finding in place when this repository owns it, file it against the owning repository when an upstream dependency in the organization owns it, and ask the operator whether to file or tackle it only when it warrants a full separate session.
- Issue-Type guidance comes from the loaded organization schema, never from a count written into the tool or the skill.
- Whether a change needs a pull request is repository-local branch policy this package does not set. Never manipulate rulesets, branch protection, or merge gating.
- GitHub access uses the operator's existing `gh` authentication; the package embeds no credentials and no organization login appears in a packaged source.
- Only the package's bounded managed block in an agent-instruction file is package-owned; the surrounding content stays consumer-owned.

Verify with `project-standards reconcile --check` and compare live organization schema with `gh-workflow audit`. See the [current adoption guide](adopt.md) for configuration, first-run expectations, and troubleshooting.
