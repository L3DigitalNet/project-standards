# GitHub Workflow Standard 1.0

- **Status:** Active; immutable package version 1.0.
- **Owner:** Project standards / repository template.
- **Last updated:** 2026-08-06.
- **Scope:** GitHub work discipline for organization-owned repositories — issues as authorized work contracts, organization-level typed issue metadata, pull requests as execution evidence, and the repo-local agent skill that binds sessions to that discipline.

---

## 1. Purpose

GitHub is the durable control plane for work in an organization-owned repository. An issue is the authorized contract for a unit of work, its organization-level fields carry the typed operational metadata that drives lifecycle decisions, and a pull request is the evidence that the contract was executed. This standard packages that operating model so a consuming repository receives one versioned, upgradeable copy of it instead of restating it as local advice.

The package delivers the model to agent sessions. An agent that is about to create or mutate GitHub work state loads the packaged skill first and follows its decision procedures, so the same discipline applies across harnesses, repositories, and sessions.

## 2. Applicability

This standard applies to repositories owned by a GitHub organization.

Personal-account repositories are out of scope. Organization-level issue fields do not exist outside an organization, and this package defines no degraded fallback that operates without them.

## 3. Configuration

The package accepts exactly two options, both required.

| Option | Type | Meaning |
| --- | --- | --- |
| `organization` | string | Login of the GitHub organization that owns the consuming repository. Must be nonempty. |
| `harnesses` | array | Agent harnesses that receive the managed instruction block. Each entry is `claude-code` or `codex`. Must be nonempty. |

Unknown options and empty values are rejected by [`config.schema.json`](config.schema.json).

```toml
[standards.github-workflow]
enabled = true
version = "1.0"

[standards.github-workflow.config]
organization = "example-org"
harnesses = ["claude-code", "codex"]
```

The package itself is organization-agnostic: no organization login appears in any packaged artifact. The `organization` option is the single place a consumer names its own organization.

## 4. Ownership boundary

The package owns its delivered artifacts and the discipline they describe. It does not own live GitHub state.

- Organization schema — issue types and organization-level issue fields — is applied by a human. The package compares live schema against its versioned baseline and reports differences; it never mutates them.
- Whether a change requires a pull request is repository-local branch policy that varies by repository. This standard does not set that threshold. Once a pull request exists, its content standard applies.
- Repository rulesets, branch protection, and merge gating stay outside the package. It never manipulates the mechanisms that judge work performed under it.
- Unmarked content in a consumer's agent-instruction files stays consumer-owned; only the package's bounded managed block is package-owned.

## 5. Adoption

[`adopt.md`](adopt.md) covers the package-specific choices. The shared control-plane lifecycle — initialization, preview, apply, disable, removal, and catalog updates — is documented by `project-standards`.
